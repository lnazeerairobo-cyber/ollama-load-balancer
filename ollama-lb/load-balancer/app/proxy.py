import httpx
from fastapi import Request, StreamingResponse
from fastapi.responses import Response
from typing import Optional
from .routing import lb
from . import config


async def proxy_request(request: Request, server_host: str, server_port: int) -> Response:
    url = f"http://{server_host}:{server_port}{request.url.path}"
    if request.url.query:
        url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()

    lb.increment_requests(server_host, server_port)

    try:
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            if request.method == "GET":
                resp = await client.get(url, headers=headers)
            elif request.method == "POST":
                resp = await client.post(url, content=body, headers=headers)
            elif request.method == "PUT":
                resp = await client.put(url, content=body, headers=headers)
            elif request.method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                resp = await client.request(request.method, url, content=body, headers=headers)

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
    except Exception as e:
        lb.mark_unhealthy(server_host, server_port)
        raise e
    finally:
        lb.decrement_requests(server_host, server_port)


async def proxy_streaming_request(request: Request, server_host: str, server_port: int) -> StreamingResponse:
    url = f"http://{server_host}:{server_port}{request.url.path}"
    if request.url.query:
        url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()

    lb.increment_requests(server_host, server_port)

    async def stream_response():
        try:
            async with httpx.AsyncClient(timeout=config.request_timeout) as client:
                async with client.stream("POST", url, content=body, headers=headers) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            lb.mark_unhealthy(server_host, server_port)
            raise e
        finally:
            lb.decrement_requests(server_host, server_port)

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
    )


def is_streaming_request(request: Request) -> bool:
    return request.url.path == "/api/generate" or request.url.path == "/api/chat"
