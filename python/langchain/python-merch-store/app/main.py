from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from app.agent import agent
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Python Merch Store - LangChain")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _extract_text(content: str | list) -> str:
    """Extract plain text from an AI message content field."""
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    config = {"configurable": {"thread_id": request.conversation_id}}
    result = await agent.ainvoke(
        {"messages": [("user", request.message)]},
        config=config,
    )
    ai_message = result["messages"][-1]
    return ChatResponse(response=_extract_text(ai_message.content))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> EventSourceResponse:
    config = {"configurable": {"thread_id": request.conversation_id}}

    async def event_generator():
        async for event in agent.astream_events(
            {"messages": [("user", request.message)]},
            config=config,
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    text = _extract_text(chunk.content)
                    if text:
                        yield {"data": text}

    return EventSourceResponse(event_generator())


# Serve the React frontend (built files from webapp/)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve static files or fall back to index.html for SPA routing."""
        file = STATIC_DIR / full_path
        if full_path and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
