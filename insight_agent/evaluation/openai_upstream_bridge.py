"""Local evaluation bridge for InsightAgent's single-prompt v2 compatibility API."""

from __future__ import annotations

import argparse
import uuid
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


def flatten_messages(messages: Any) -> str:
    """Preserve every OpenAI message in one prompt for the legacy upstream."""

    if isinstance(messages, str):
        return messages
    parts: list[str] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").upper()
        content = item.get("content")
        if isinstance(content, list):
            content = "\n".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        parts.append(f"[{role}]\n{str(content or '')}")
    return "\n\n".join(parts)


def create_app(upstream: str) -> FastAPI:
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        body = await request.json()
        stream = bool(body.get("stream"))
        upstream_body = dict(body)
        upstream_body["messages"] = [
            {"role": "user", "content": flatten_messages(body.get("messages"))}
        ]
        upstream_body["conv_uid"] = f"week4-bridge-{uuid.uuid4()}"
        upstream_body["chat_mode"] = "chat_normal"
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(180.0, connect=10.0),
            trust_env=False,
        )
        if stream:
            outgoing = client.build_request("POST", upstream, json=upstream_body)
            try:
                response = await client.send(outgoing, stream=True)
                response.raise_for_status()
            except Exception:
                await client.aclose()
                raise

            async def chunks():
                try:
                    async for data in response.aiter_raw():
                        yield data
                finally:
                    await response.aclose()
                    await client.aclose()

            return StreamingResponse(chunks(), media_type="text/event-stream")
        try:
            response = await client.post(upstream, json=upstream_body)
            response.raise_for_status()
            payload = response.json()
        finally:
            await client.aclose()
        return JSONResponse(payload)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        default="http://127.0.0.1:5670/api/v2/chat/completions",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5673)
    args = parser.parse_args()
    uvicorn.run(create_app(args.upstream), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
