from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.pairs import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_get_pairs_returns_list():
    response = client.get("/pairs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "EUR/USD" in data
    assert "BTC/USD" in data
    assert len(data) == 10
