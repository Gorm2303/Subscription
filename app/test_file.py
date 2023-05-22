import pytest
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

from app import app

@pytest.fixture
def test_user():
    client = MongoClient(os.environ.get("MONGO_URI"))
    db = client["subscriptiondb"]
    subsCollection = db["subscriptions"]
    subsCollection.delete_many({"user_id": "test_user"})
    yield
    subsCollection.delete_many({"user_id": "test_user"})

# Test subscription type endpoint
def test_get_subscription_types():
    client = app.test_client()
    response = client.get("/subscriptiontypes")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert "id" in item
        assert "price" in item
        assert "description" in item

# Test subscription creation endpoint
def test_create_subscription(test_user):
    client = app.test_client()
    client.post("/subscriptions", json={
        "user_id": "test_user",
        "subscription_type_id": 1
    })
    # Verify that subscription was created
    now = datetime.utcnow()
    client = MongoClient(os.environ.get("MONGO_URI"))
    db = client["subscriptiondb"]
    subsCollection = db["subscriptions"]
    subscription = subsCollection.find_one({"user_id": "test_user", "expiration_date": {"$gt": now}})
    assert subscription is not None
    # Verify that subscription expiration date is correct
    days_valid = 30
    expiration_date = now + timedelta(days=days_valid)
    assert abs((subscription["expiration_date"] - expiration_date).total_seconds()) <= 10


# Test subscription status endpoint
def test_check_subscription(test_user):
    client = app.test_client()
    # Verify that user without active subscription returns 404
    response = client.get("/subscriptions/nonexistent_user/active")
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "msg" in data
    assert data["msg"] == "User does not have an active subscription"
    # Create subscription for test_user
    client.post("/subscriptions", json={
        "user_id": "test_user",
        "subscription_type_id": 1
    })
    # Verify that user with active subscription returns 200
    response = client.get("/subscriptions/test_user/active")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "msg" in data
    assert data["msg"] == "User has an active subscription"
