from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import asyncio, json

router = APIRouter()
connected: list[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected.append(ws)
    try:
        while True:
            await asyncio.sleep(30)  # keepalive ping
    except WebSocketDisconnect:
        connected.remove(ws)

async def broadcast(event: dict):
    dead = []
    for ws in connected:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected:
            connected.remove(ws)


@router.post("/ws/test-anomaly")
async def test_anomaly():
    from datetime import datetime, timezone
    event = {
        "type": "anomaly",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "layer_type": "aq",
            "zone_name": "Anand Vihar",
            "value": 315.4,
            "confidence": 0.89,
            "cause": "crop_burning",
            "explanation": "AQI spiked to 315 (Very Poor) due to seasonal crop residue burning upwind."
        }
    }
    await broadcast(event)
    return {"status": "success", "message": "Broadcasted test anomaly"}
