# Claude Chat Stream Proxy

A Go application that exposes a streaming HTTP API on top of the Claude CLI. It keeps a **long-lived `claude` process per session** using bidirectional stream-json, so conversation context is preserved across multiple requests — just like a real interactive CLI session.

## Prerequisites

- Go 1.21+
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

## Build

```bash
go build -o claude-proxy .
```

## Run

```bash
./claude-proxy
```

By default the server listens on port `8080`. Override with the `PORT` environment variable:

```bash
PORT=3000 ./claude-proxy
```

## API

### `POST /api/chat/stream`

Sends a prompt to Claude and streams the response as SSE events.

- If `session_id` is omitted, a **new session** is created (spawns a new `claude` process).
- If `session_id` is provided, the message is sent to the **existing session**, preserving full conversation history.

**Request body**

| Field        | Type   | Required | Description                                           |
|--------------|--------|----------|-------------------------------------------------------|
| `prompt`     | string | yes      | The message to send to Claude                         |
| `session_id` | string | no       | Reuse an existing session (returned in `X-Session-ID` header) |

**Response**

- **Headers**: `X-Session-ID` contains the session ID for follow-up requests.
- **Body**: a stream of `text/event-stream` events. Each `data:` line contains a JSON object emitted by the Claude CLI. The stream ends with `data: [DONE]` when the turn completes.

### `DELETE /api/sessions/{sessionID}`

Terminates a session and kills its `claude` process.

## How it works

1. On the first request (no `session_id`), the server spawns:
   ```
   claude --print --verbose --output-format stream-json --input-format stream-json
   ```
2. The process stays alive. Each new message is written to the process's **stdin** as a JSON object.
3. The server reads JSON events from **stdout** and forwards them as SSE until a `result` message marks the end of the turn.
4. The session is reusable — send more messages with the same `session_id` to continue the conversation.
5. When you're done, `DELETE /api/sessions/{id}` to clean up, or let the server handle it on shutdown.

## Docker

### Build the image

```bash
docker build -t claude-proxy .
```

### Run the container

Pass your Anthropic API key at runtime:

```bash
docker run -p 8080:8080 -e ANTHROPIC_API_KEY=sk-ant-... claude-proxy
```

## OpenTelemetry / Dash0 Integration

Claude Code has built-in OpenTelemetry support. All `OTEL_*` and `CLAUDE_CODE_*` environment variables set on the process (or container) are automatically inherited by the `claude` CLI child process.

Because sessions are now long-lived, OTel exporters have time to flush normally. The Dockerfile still sets short export intervals (`1000ms`) as a safety net.

### Required environment variables

| Variable | Description | Example |
|---|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | Enables telemetry collection (required) | `1` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Dash0 OTLP endpoint | `https://ingress.us1.dash0.com` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth header for Dash0 | `Authorization=Bearer your-dash0-token` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | OTLP wire protocol | `grpc` or `http/protobuf` |

### Exporter selection

| Variable | Description | Example Values |
|---|---|---|
| `OTEL_METRICS_EXPORTER` | Metrics exporter | `otlp`, `console`, `prometheus`, `none` |
| `OTEL_LOGS_EXPORTER` | Logs/events exporter | `otlp`, `console`, `none` |
| `OTEL_TRACES_EXPORTER` | Traces exporter (beta — also requires `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`) | `otlp`, `console`, `none` |

### Optional tuning variables

| Variable | Description | Default |
|---|---|---|
| `OTEL_METRIC_EXPORT_INTERVAL` | Metrics export interval (ms) | `60000` |
| `OTEL_LOGS_EXPORT_INTERVAL` | Logs export interval (ms) | `5000` |
| `OTEL_TRACES_EXPORT_INTERVAL` | Traces batch export interval (ms) | `5000` |
| `OTEL_LOG_USER_PROMPTS` | Include user prompt text in events | disabled |
| `OTEL_LOG_TOOL_DETAILS` | Include tool parameters in events | disabled |
| `OTEL_LOG_TOOL_CONTENT` | Include tool input/output in trace spans | disabled |
| `OTEL_RESOURCE_ATTRIBUTES` | Custom resource attributes for team/cost-center tagging | `team=platform,env=prod` |

### Run locally with Dash0

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_TRACES_EXPORTER=otlp
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://ingress.us1.dash0.com
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <your-dash0-token>"

./claude-proxy
```

### Run in Docker with Dash0

The Dockerfile already sets `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` and all export intervals to `1000ms`, so you only need to pass the Dash0-specific variables:

```bash
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e CLAUDE_CODE_ENABLE_TELEMETRY=1 \
  -e OTEL_METRICS_EXPORTER=otlp \
  -e OTEL_LOGS_EXPORTER=otlp \
  -e OTEL_TRACES_EXPORTER=otlp \
  -e CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=https://ingress.us1.dash0.com \
  -e 'OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <your-dash0-token>,Dash0-Dataset=claude' \
  claude-proxy
```

### What gets exported

- **Metrics**: session count, token usage, cost, lines of code changed, commits, PRs, active time
- **Events/Logs**: user prompts, API requests/errors, tool results, tool decisions, compaction
- **Traces (beta)**: distributed spans linking each prompt to its API calls and tool executions

For full details see the [Claude Code monitoring docs](https://code.claude.com/docs/en/monitoring-usage).

## Examples

### Start a new conversation

```bash
curl -N -X POST http://localhost:8080/api/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Hello, what can you do?"}'
```

Note the `X-Session-ID` response header — you'll need it for follow-up messages.

### Continue the conversation

```bash
curl -N -X POST http://localhost:8080/api/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Tell me more about that", "session_id":"<X-Session-ID from above>"}'
```

### End a session

```bash
curl -X DELETE http://localhost:8080/api/sessions/<session-id>
```
