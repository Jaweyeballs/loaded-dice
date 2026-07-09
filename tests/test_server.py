from fastapi.testclient import TestClient

from loaded_dice.server import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_room():
    client = TestClient(app)
    response = client.post("/rooms", json={"starting_chips": 1000})
    assert response.status_code == 200
    code = response.json()["room_code"]
    assert len(code) == 4


def test_websocket_join_and_host_start():
    client = TestClient(app)
    code = client.post("/rooms").json()["room_code"]

    with client.websocket_connect(f"/ws/{code}") as alice:
        alice.send_json({"type": "join", "player_name": "Alice"})
        joined = alice.receive_json()
        assert joined["type"] == "joined"
        assert joined["payload"]["host_name"] == "Alice"
        # Drain join broadcast
        alice.receive_json()

        alice.send_json({"type": "start"})
        err = alice.receive_json()
        assert err["type"] == "error"
        assert "at least 2" in err["message"].lower()
