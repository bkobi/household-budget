import pytest, os, tempfile
import app as app_module
from app import create_app

@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test.db")
    app_module.DB_PATH = db_file
    application = create_app({"TESTING": True, "DB_PATH": db_file})
    with application.test_client() as c:
        yield c

def test_add_transaction(client):
    res = client.post("/api/transactions/", json={
        "description": "סופרמרקט", "amount": 250.0,
        "category": "food", "date": "2024-03-15",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["description"] == "סופרמרקט"
    assert data["amount"] == 250.0

def test_invalid_category(client):
    res = client.post("/api/transactions/", json={
        "description": "test", "amount": 100,
        "category": "invalid_cat", "date": "2024-03-15",
    })
    assert res.status_code == 400

def test_negative_amount(client):
    res = client.post("/api/transactions/", json={
        "description": "test", "amount": -50,
        "category": "food", "date": "2024-03-15",
    })
    assert res.status_code == 400

def test_list_filtered(client):
    client.post("/api/transactions/", json={"description":"מרץ","amount":100,"category":"food","date":"2024-03-10"})
    client.post("/api/transactions/", json={"description":"אפריל","amount":200,"category":"food","date":"2024-04-01"})
    res  = client.get("/api/transactions/?month=3&year=2024")
    txns = res.get_json()
    assert len(txns) == 1
    assert txns[0]["description"] == "מרץ"

def test_set_budget(client):
    res = client.post("/api/budget/category", json={
        "month":3,"year":2024,"category":"food","amount":2000
    })
    assert res.status_code == 200
    assert res.get_json()["amount"] == 2000

def test_set_income(client):
    res = client.post("/api/budget/income", json={"month":3,"year":2024,"amount":15000})
    assert res.status_code == 200
    assert res.get_json()["amount"] == 15000

def test_summary(client):
    client.post("/api/budget/income",   json={"month":3,"year":2024,"amount":10000})
    client.post("/api/budget/category", json={"month":3,"year":2024,"category":"food","amount":3000})
    client.post("/api/transactions/",   json={"description":"שופרסל","amount":500,"category":"food","date":"2024-03-05"})
    res  = client.get("/api/stats/summary?month=3&year=2024")
    data = res.get_json()
    assert data["income"] == 10000
    assert data["total_spent"] == 500
    assert data["remaining"] == 9500

def test_alerts_warning(client):
    client.post("/api/budget/category", json={"month":3,"year":2024,"category":"food","amount":1000})
    client.post("/api/transactions/",   json={"description":"קניות","amount":850,"category":"food","date":"2024-03-10"})
    res    = client.get("/api/budget/alerts?month=3&year=2024")
    alerts = res.get_json()
    assert len(alerts) == 1
    assert alerts[0]["level"] == "warning"

def test_delete_transaction(client):
    res    = client.post("/api/transactions/", json={"description":"test","amount":100,"category":"food","date":"2024-03-01"})
    txn_id = res.get_json()["id"]
    assert client.delete(f"/api/transactions/{txn_id}").status_code == 200
    assert client.get("/api/transactions/?month=3&year=2024").get_json() == []

def test_update_transaction(client):
    res    = client.post("/api/transactions/", json={"description":"ישן","amount":100,"category":"food","date":"2024-03-01"})
    txn_id = res.get_json()["id"]
    upd    = client.put(f"/api/transactions/{txn_id}", json={"description":"חדש","amount":200})
    assert upd.status_code == 200
    assert upd.get_json()["description"] == "חדש"
    assert upd.get_json()["amount"] == 200

def test_trend(client):
    client.post("/api/transactions/", json={"description":"ינואר","amount":1000,"category":"food","date":"2024-01-10"})
    client.post("/api/transactions/", json={"description":"מרץ",  "amount":500, "category":"food","date":"2024-03-05"})
    res   = client.get("/api/stats/trend?year=2024")
    trend = res.get_json()
    assert len(trend) == 12
    assert trend[0]["total"] == 1000   # January (index 0)
    assert trend[2]["total"] == 500    # March   (index 2)
