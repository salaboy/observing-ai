# Python Merch Store (Otel Langchain Instrumented)

**Note:** This version of the application is using the [Langchain Otel Instrumentation](https://pypi.org/project/opentelemetry-instrumentation-langchain/)

An AI-powered merch store chatbot for Python community projects. Chat with the store assistant to browse T-Shirts, Socks, and Stickers from projects like NumPy, Pandas, PyTorch, TensorFlow, LangChain, and more. The assistant can look up inventory, show product cards, and place orders on your behalf.

Built with [LangChain](https://docs.langchain.com) + [LangGraph](https://langchain-ai.github.io/langgraph/) for the AI agent, [Claude](https://docs.anthropic.com) as the LLM, [FastAPI](https://fastapi.tiangolo.com) for the backend, and a React/TypeScript frontend with a retro Windows 95 theme toggle.



## Architecture

```
┌─────────────────────────────────────────────┐
│  React Frontend (webapp/)                   │
│  - Chat UI with streaming messages          │
│  - Merch card rendering from <merch-items>  │
│  - Order confirmation display               │
│  - Modern / Retro theme toggle              │
└────────────────┬────────────────────────────┘
                 │ POST /api/chat/stream (SSE)
                 │ POST /api/chat
┌────────────────▼────────────────────────────┐
│  FastAPI (app/main.py)                      │
│  - Serves API + built static files          │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  LangGraph ReAct Agent (app/agent.py)       │
│  - Claude model + system prompt             │
│  - In-memory chat history (MemorySaver)     │
│  - 4 tools:                                 │
│    get_item_stock, display_merch_images,     │
│    place_order, list_all_items              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  In-Memory Inventory (app/inventory.py)     │
│  - 30 merch items across 11 Python projects │
└─────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- An [Anthropic API key](https://console.anthropic.com/)

### Installing Python on macOS

If you install Python via Homebrew, `pip` is not included by default. Use a virtual environment instead, which is the recommended approach:

```bash
brew install python

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

Once the virtual environment is active, `pip` is available and all packages will be installed locally to the project. You'll see `(.venv)` in your shell prompt.

> **Note:** Run `source .venv/bin/activate` each time you open a new terminal before working with the project.

## Setup

### 1. Build the React frontend

```bash
cd webapp
npm install
npm run build
cd ..
```

This compiles the TypeScript and bundles the React app into the `static/` directory, which FastAPI serves automatically.

### 2. Install Python dependencies

```bash
pip install -e .
```

### 3. Set your API key

```bash
export ANTHROPIC_API_KEY=your-key-here
```

### 4. Run the application

```bash
python -m app.main
```

The server starts on **http://localhost:8080**. Open it in your browser to use the chat UI.

## Docker

The multi-stage Dockerfile builds the React frontend and installs Python dependencies in a single image — no local Python or Node.js required.

### Build the image

```bash
docker build -t python-merch-store .
```

### Push to a container registry

Tag the image for your registry and push it. Replace `your-registry.com/your-org` with your actual registry URL (e.g. Docker Hub, GitHub Container Registry, AWS ECR, Google Artifact Registry):

```bash
# Docker Hub
docker tag python-merch-store your-dockerhub-user/python-merch-store:latest
docker push your-dockerhub-user/python-merch-store:latest

# GitHub Container Registry
docker tag python-merch-store ghcr.io/your-org/python-merch-store:latest
docker push ghcr.io/your-org/python-merch-store:latest
```

You may need to authenticate first with `docker login` (Docker Hub) or `echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin` (GHCR).

### Run the container

Minimal run (no observability):

```bash
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=your-key-here \
  python-merch-store
```

With Dash0 observability:

```bash
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=your-key-here \
  -e OTEL_SERVICE_NAME=python-merch-store \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=<your-dash0-endpoint> \
  -e OTEL_EXPORTER_OTLP_HEADERS_AUTHORIZATION=<your-dash0-auth-token> \
  -e DASH0_DATASET=<your-dash0-dataset> \
  -e 'OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <your-dash0-auth-token>,Dash0-Dataset=<your-dash0-dataset>' \
  python-merch-store
```

The server starts on **http://localhost:8080**.

## Development

To develop the frontend with hot-reload, run the Vite dev server and the Python backend separately:

**Terminal 1 -- Python backend:**

```bash
python -m app.main
```

**Terminal 2 -- Vite dev server:**

```bash
cd webapp
npm run dev
```

The Vite dev server runs on http://localhost:5173 and proxies `/api` requests to `http://localhost:8080`.

## Observability with Dash0

The application is instrumented with [OpenTelemetry](https://opentelemetry.io/) using the [`opentelemetry-instrumentation-langchain`](https://pypi.org/project/opentelemetry-instrumentation-langchain/) package. This automatically traces all LangChain/LangGraph operations — LLM calls, tool invocations, and agent reasoning steps — and exports them via OTLP.

To send telemetry data to [Dash0](https://www.dash0.com/), set the following environment variables before starting the application:

```bash
export OTEL_SERVICE_NAME=python-merch-store
export OTEL_EXPORTER_OTLP_HEADERS_AUTHORIZATION=<your-dash0-auth-token>
export DASH0_DATASET=<your dash0 dataset>
export OTEL_EXPORTER_OTLP_ENDPOINT=<your-dash0-endpoint>
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer ${OTEL_EXPORTER_OTLP_HEADERS_AUTHORIZATION},Dash0-Dataset=${DASH0_DATASET}"

```

| Variable | Description |
|----------|-------------|
| `OTEL_SERVICE_NAME` | Identifies this service in Dash0 (e.g. `python-merch-store`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Dash0 OTLP ingestion endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth and dataset headers sent with every OTLP request |
| `OTEL_EXPORTER_OTLP_HEADERS_AUTHORIZATION` | Your Dash0 API auth token (found in Dash0 settings) |
| `DASH0_DATASET` | Dash0 dataset to route data to (use `default` if unsure) |

To disable prompt/completion content capture for privacy, set:

```bash
export TRACELOOP_TRACE_CONTENT=false
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Synchronous chat -- returns the full response |
| `POST` | `/api/chat/stream` | Streaming chat via Server-Sent Events |

Both endpoints accept:

```json
{
  "conversation_id": "unique-session-id",
  "message": "What NumPy merch do you have?"
}
```

## Project Structure

```
python-merch-store/
├── app/
│   ├── main.py          # FastAPI app, API routes, static file serving
│   ├── agent.py         # LangGraph agent with Claude, tools, and system prompt
│   ├── tools.py         # 4 tool functions (stock, display, order, list)
│   ├── inventory.py     # In-memory inventory (30 items, 11 projects)
│   ├── memory.py        # MemorySaver checkpointer for conversation history
│   └── models.py        # Pydantic models (MerchItem, OrderLine, ChatRequest, etc.)
├── webapp/              # React/TypeScript frontend source
│   ├── src/
│   │   ├── App.tsx      # Main chat UI component
│   │   └── main.tsx     # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── static/              # Built frontend (generated by npm run build)
├── pyproject.toml
└── README.md
```
