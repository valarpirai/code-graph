import os
import httpx

BASE_URL = os.getenv("CODE_GRAPH_URL", "http://localhost:8000")


def get_client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


def handle_response(resp: httpx.Response) -> dict:
    if resp.status_code == 204:
        return {}
    if resp.status_code >= 400:
        try:
            body = resp.json()
            detail = body.get("detail") or body
        except Exception:
            detail = resp.text
        raise ValueError(f"Backend {resp.status_code}: {detail}")
    return resp.json()
