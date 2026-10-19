import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("What-If:")
res = client.post("/api/twins/DT-01/what-if", json={"carbs_g": 60.0, "activity_level": "moderate"})
print(res.status_code, res.json())

print("Replay:")
import asyncio
async def test_replay():
    from backend.app.services.twin_service import twin_service
    await twin_service.start_replay("DT-01", 10.0)
    print("Replay task:", twin_service._replay_tasks["DT-01"])
    await asyncio.sleep(0.5)
    print("Replay task done?", twin_service._replay_tasks["DT-01"].done())
    if twin_service._replay_tasks["DT-01"].done():
        print("Exception:", twin_service._replay_tasks["DT-01"].exception())

asyncio.run(test_replay())
