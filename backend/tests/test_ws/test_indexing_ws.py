# tests/test_ws/test_indexing_ws.py
import pytest
from app.ws.indexing import IndexingNotifier, IndexingEvent

@pytest.mark.asyncio
async def test_notifier_registers_and_sends():
    notifier = IndexingNotifier()
    messages = []

    async def fake_send(msg):
        messages.append(msg)

    notifier.register("test-proj", fake_send)
    await notifier.notify("test-proj", IndexingEvent(status="indexing", progress=0.5, message="Parsing..."))
    assert len(messages) == 1
    assert messages[0]["status"] == "indexing"
    assert messages[0]["progress"] == 0.5

@pytest.mark.asyncio
async def test_notifier_unregister():
    notifier = IndexingNotifier()
    messages = []

    async def fake_send(msg):
        messages.append(msg)

    notifier.register("p1", fake_send)
    notifier.unregister("p1")
    await notifier.notify("p1", IndexingEvent(status="done", progress=1.0, message="Done"))
    assert len(messages) == 0  # unregistered, no message sent
