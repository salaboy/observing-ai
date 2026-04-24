package main

import (
	"bufio"
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
)

// ChatRequest is the JSON body the client sends.
type ChatRequest struct {
	Prompt    string `json:"prompt"`
	SessionID string `json:"session_id,omitempty"`
}

// streamInputMessage is written to Claude's stdin in stream-json mode.
type streamInputMessage struct {
	Type    string      `json:"type"`
	Message userMessage `json:"message"`
}

type userMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Session holds a long-lived claude process.
type Session struct {
	ID     string
	cmd    *exec.Cmd
	stdin  io.WriteCloser
	cancel context.CancelFunc

	mu    sync.Mutex   // serialize requests – one turn at a time
	lines chan string   // background goroutine pushes stdout lines here
	done  chan struct{} // closed when the process exits
}

// SendMessage writes a user message to Claude's stdin.
func (s *Session) SendMessage(prompt string) error {
	msg := streamInputMessage{
		Type: "user",
		Message: userMessage{
			Role:    "user",
			Content: prompt,
		},
	}
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	data = append(data, '\n')
	_, err = s.stdin.Write(data)
	return err
}

// Close terminates the claude process and cleans up.
func (s *Session) Close() {
	s.stdin.Close()
	s.cancel()
}

// SessionManager stores active sessions.
type SessionManager struct {
	mu       sync.RWMutex
	sessions map[string]*Session
}

func NewSessionManager() *SessionManager {
	return &SessionManager{sessions: make(map[string]*Session)}
}

func (sm *SessionManager) Get(id string) *Session {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.sessions[id]
}

func (sm *SessionManager) Set(id string, s *Session) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	sm.sessions[id] = s
}

func (sm *SessionManager) Delete(id string) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	delete(sm.sessions, id)
}

var mgr = NewSessionManager()

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Content-Type"},
		AllowCredentials: false,
	}))

	r.Post("/api/chat/stream", handleChatStream)
	r.Delete("/api/sessions/{sessionID}", handleDeleteSession)

	log.Printf("Server listening on :%s", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func generateID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 1
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}

// createSession spawns a long-lived claude process with bidirectional streaming.
func createSession() (*Session, error) {
	ctx, cancel := context.WithCancel(context.Background())

	args := []string{
		"--print",
		"--verbose",
		"--output-format", "stream-json",
		"--input-format", "stream-json",
	}

	cmd := exec.CommandContext(ctx, "claude", args...)

	stdinPipe, err := cmd.StdinPipe()
	if err != nil {
		cancel()
		return nil, fmt.Errorf("stdin pipe: %w", err)
	}

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		cancel()
		return nil, fmt.Errorf("stdout pipe: %w", err)
	}

	cmd.Stderr = os.Stderr // surface claude errors in server logs

	if err := cmd.Start(); err != nil {
		cancel()
		return nil, fmt.Errorf("start claude: %w", err)
	}

	id := generateID()
	s := &Session{
		ID:     id,
		cmd:    cmd,
		stdin:  stdinPipe,
		cancel: cancel,
		lines:  make(chan string, 512),
		done:   make(chan struct{}),
	}

	// Background reader: push every stdout line into the channel.
	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
		for scanner.Scan() {
			line := scanner.Text()
			if line != "" {
				s.lines <- line
			}
		}
		_ = cmd.Wait()
		close(s.done)
		mgr.Delete(s.ID)
		log.Printf("session %s: process exited", s.ID)
	}()

	mgr.Set(id, s)
	log.Printf("session %s: created", id)
	return s, nil
}

func handleChatStream(w http.ResponseWriter, r *http.Request) {
	var req ChatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}
	if req.Prompt == "" {
		http.Error(w, `{"error":"prompt is required"}`, http.StatusBadRequest)
		return
	}

	var s *Session
	var isNew bool

	if req.SessionID != "" {
		s = mgr.Get(req.SessionID)
		if s == nil {
			http.Error(w, `{"error":"session not found"}`, http.StatusNotFound)
			return
		}
	} else {
		var err error
		s, err = createSession()
		if err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%v"}`, err), http.StatusInternalServerError)
			return
		}
		isNew = true
	}

	// One turn at a time per session.
	s.mu.Lock()
	defer s.mu.Unlock()

	// SSE headers.
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Session-ID", s.ID)

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, `{"error":"streaming not supported"}`, http.StatusInternalServerError)
		return
	}

	// For new sessions, wait for the init event before sending the first message.
	if isNew {
		if err := waitForInit(s, w, flusher); err != nil {
			writeSSEError(w, flusher, err.Error())
			return
		}
	}

	// Send the user message to Claude's stdin.
	if err := s.SendMessage(req.Prompt); err != nil {
		writeSSEError(w, flusher, fmt.Sprintf("failed to send message: %v", err))
		return
	}

	// Stream events until the turn completes (result message).
	streamUntilResult(s, w, flusher, r.Context())

	fmt.Fprintf(w, "data: [DONE]\n\n")
	flusher.Flush()
}

func handleDeleteSession(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "sessionID")
	s := mgr.Get(id)
	if s == nil {
		http.Error(w, `{"error":"session not found"}`, http.StatusNotFound)
		return
	}
	s.Close()
	mgr.Delete(id)
	log.Printf("session %s: deleted by client", id)
	w.WriteHeader(http.StatusNoContent)
}

// waitForInit reads events until the system/init message arrives, forwarding
// everything to the SSE client. Gives up after 30 seconds.
func waitForInit(s *Session, w http.ResponseWriter, flusher http.Flusher) error {
	timeout := time.After(30 * time.Second)
	for {
		select {
		case line := <-s.lines:
			if !json.Valid([]byte(line)) {
				continue
			}
			fmt.Fprintf(w, "data: %s\n\n", line)
			flusher.Flush()

			var ev struct {
				Type    string `json:"type"`
				Subtype string `json:"subtype"`
			}
			if json.Unmarshal([]byte(line), &ev) == nil {
				if ev.Type == "system" && ev.Subtype == "init" {
					return nil
				}
			}
		case <-s.done:
			return fmt.Errorf("claude process exited during initialization")
		case <-timeout:
			return fmt.Errorf("timeout waiting for claude to initialize")
		}
	}
}

// streamUntilResult forwards stdout events as SSE until a "result" message
// signals the end of the turn.
func streamUntilResult(s *Session, w http.ResponseWriter, flusher http.Flusher, ctx context.Context) {
	for {
		select {
		case line := <-s.lines:
			if !json.Valid([]byte(line)) {
				continue
			}
			fmt.Fprintf(w, "data: %s\n\n", line)
			flusher.Flush()

			var ev struct {
				Type string `json:"type"`
			}
			if json.Unmarshal([]byte(line), &ev) == nil && ev.Type == "result" {
				return
			}
		case <-s.done:
			return
		case <-ctx.Done():
			// Client disconnected — session stays alive for future use.
			return
		}
	}
}

func writeSSEError(w http.ResponseWriter, flusher http.Flusher, msg string) {
	data, _ := json.Marshal(map[string]string{"type": "error", "error": msg})
	fmt.Fprintf(w, "data: %s\n\n", data)
	flusher.Flush()
}
