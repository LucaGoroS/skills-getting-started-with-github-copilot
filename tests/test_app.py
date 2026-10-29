from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_participants = {
        activity_name: list(activity["participants"])
        for activity_name, activity in activities.items()
    }
    yield TestClient(app, follow_redirects=False)
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants


def test_root_redirects_to_homepage(client):
    response = client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_expected_shape(client):
    response = client.get("/activities")

    assert response.status_code == 200
    result = response.json()
    assert result
    for activity in result.values():
        assert {"description", "schedule", "max_participants", "participants"} <= activity.keys()
        assert isinstance(activity["description"], str)
        assert isinstance(activity["schedule"], str)
        assert isinstance(activity["max_participants"], int)
        assert isinstance(activity["participants"], list)


def test_signup_adds_participant(client):
    activity_name = next(iter(activities))
    email = "new.student@example.com"

    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in client.get("/activities").json()[activity_name]["participants"]


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        "/activities/Unknown%20Activity/signup",
        params={"email": "new.student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant(client):
    activity_name, activity = next(
        (name, activity)
        for name, activity in activities.items()
        if activity["participants"]
    )
    email = activity["participants"][0]
    original_participants = list(activity["participants"])

    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert client.get("/activities").json()[activity_name]["participants"] == original_participants


def test_unregister_removes_participant_and_preserves_others(client):
    activity_name, activity = next(
        (name, activity)
        for name, activity in activities.items()
        if activity["participants"]
    )
    email = activity["participants"][0]
    expected_participants = [
        participant for participant in activity["participants"] if participant != email
    ]

    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert client.get("/activities").json()[activity_name]["participants"] == expected_participants


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Activity/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_unregistered_participant(client):
    activity_name = next(iter(activities))

    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": "unregistered.student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"