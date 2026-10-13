from datetime import datetime, timedelta

import pytest
from sqlalchemy import update

from models import IssueModel


def test_create_issue(create_issue):
    issue = create_issue(title="Fix login page", priority="high")
    assert isinstance(issue["id"], int)
    assert issue["id"] > 0
    assert issue["title"] == "Fix login page"
    assert issue["priority"] == "high"
    assert issue["status"] == "open"
    assert isinstance(datetime.fromisoformat(issue["created_at"]), datetime)
    assert isinstance(datetime.fromisoformat(issue["updated_at"]), datetime)


def test_get_issue(client, create_issue):
    issue = create_issue()
    response = client.get(f"/issues/{issue['id']}")
    assert response.status_code == 200
    assert response.json() == issue


def test_get_nonexistent_issue(client):
    response = client.get("/issues/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Issue not found"}


def test_update_issue(client, create_issue, db_engine):
    issue = create_issue()
    old_timestamp = datetime(2000, 1, 1)
    # Seed an old timestamp so SQLite's one-second precision needs no sleeps.
    with db_engine.begin() as connection:
        connection.execute(
            update(IssueModel)
            .where(IssueModel.id == issue["id"])
            .values(updated_at=old_timestamp)
        )
    response = client.put(
        f"/issues/{issue['id']}",
        json={"title": "Login fixed", "status": "closed", "priority": "low"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Login fixed"
    assert updated["status"] == "closed"
    assert updated["priority"] == "low"
    assert updated["created_at"] == issue["created_at"]
    assert datetime.fromisoformat(updated["updated_at"]) > old_timestamp
    assert datetime.fromisoformat(updated["updated_at"]) >= datetime.fromisoformat(
        issue["created_at"]
    )
    assert client.get(f"/issues/{issue['id']}").json() == updated


def test_update_nonexistent_issue(client):
    response = client.put("/issues/999999", json={"title": "Missing"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Issue not found"}
    assert client.get("/issues").json() == []


def test_delete_issue(client, create_issue):
    issue = create_issue()
    response = client.delete(f"/issues/{issue['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/issues/{issue['id']}").status_code == 404


def test_delete_nonexistent_issue(client):
    response = client.delete("/issues/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Issue not found"}


def test_invalid_priority(client):
    response = client.post(
        "/issues", json={"title": "Valid", "description": "Details", "priority": "urgent"}
    )
    assert response.status_code == 422


def test_invalid_status(client, create_issue):
    issue = create_issue()
    response = client.put(f"/issues/{issue['id']}", json={"status": "invalid"})
    assert response.status_code == 422
    assert client.get(f"/issues/{issue['id']}").json() == issue


@pytest.mark.parametrize("title", ["", "   ", "x" * 101])
def test_invalid_create_title(client, title):
    response = client.post("/issues", json={"title": title, "description": "Details"})
    assert response.status_code == 422


@pytest.mark.parametrize("title", ["", "   ", "x" * 101])
def test_invalid_update_title(client, create_issue, title):
    issue = create_issue()
    response = client.put(f"/issues/{issue['id']}", json={"title": title})
    assert response.status_code == 422


def test_trimmed_fields(client, create_issue):
    issue = create_issue(title="  Valid title  ", description="  Details  ")
    assert issue["title"] == "Valid title"
    assert issue["description"] == "Details"
    response = client.put(
        f"/issues/{issue['id']}", json={"title": "  Updated  ", "description": "  New  "}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["description"] == "New"


def test_description_length(client, create_issue):
    issue = create_issue(description="x" * 1000)
    response = client.post("/issues", json={"title": "Valid", "description": "x" * 1001})
    assert response.status_code == 422
    response = client.put(f"/issues/{issue['id']}", json={"description": "x" * 1001})
    assert response.status_code == 422


def test_filtering(client, create_issue):
    open_high = create_issue(priority="high")
    open_low = create_issue(priority="low")
    closed_high = create_issue(priority="high")
    response = client.put(f"/issues/{closed_high['id']}", json={"status": "closed"})
    assert response.status_code == 200

    for params, expected_ids in [
        ({"status": "open"}, [open_high["id"], open_low["id"]]),
        ({"priority": "high"}, [open_high["id"], closed_high["id"]]),
        ({"status": "open", "priority": "high"}, [open_high["id"]]),
        ({"status": "closed", "priority": "low"}, []),
    ]:
        response = client.get("/issues", params=params)
        assert response.status_code == 200
        assert [issue["id"] for issue in response.json()] == expected_ids


def test_pagination(client, create_issue):
    ids = [create_issue(title=f"Issue {i}")["id"] for i in range(5)]
    for offset, expected in [(0, ids[:2]), (2, ids[2:4]), (10, [])]:
        response = client.get("/issues", params={"limit": 2, "offset": offset})
        assert response.status_code == 200
        assert len(response.json()) == len(expected)
        assert [issue["id"] for issue in response.json()] == expected


def test_default_page_size(client, create_issue):
    ids = [create_issue(title=f"Issue {i}")["id"] for i in range(21)]
    response = client.get("/issues")
    assert response.status_code == 200
    assert [issue["id"] for issue in response.json()] == ids[:20]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_invalid_pagination(client, params):
    assert client.get("/issues", params=params).status_code == 422


@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_id_sorting(client, create_issue, direction):
    ids = [create_issue(title=f"Issue {i}")["id"] for i in range(4)]
    response = client.get("/issues", params={"sort_by": "id", "sort_order": direction})
    assert response.status_code == 200
    assert [issue["id"] for issue in response.json()] == sorted(ids, reverse=direction == "desc")


@pytest.mark.parametrize("field", ["created_at", "updated_at"])
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_timestamp_sorting(client, create_issue, db_engine, field, direction):
    ids = [create_issue(title=f"Issue {i}")["id"] for i in range(3)]
    earlier = datetime(2000, 1, 1)
    later = earlier + timedelta(days=1)
    with db_engine.begin() as connection:
        for issue_id, timestamp in zip(ids, [later, earlier, later]):
            connection.execute(
                update(IssueModel).where(IssueModel.id == issue_id).values({field: timestamp})
            )
    response = client.get("/issues", params={"sort_by": field, "sort_order": direction})
    assert response.status_code == 200
    expected = [ids[1], ids[0], ids[2]] if direction == "asc" else [ids[0], ids[2], ids[1]]
    assert [issue["id"] for issue in response.json()] == expected


def test_filter_sort_and_paginate(client, create_issue):
    matching = []
    for i in range(4):
        matching.append(create_issue(title=f"High {i}", priority="high")["id"])
        create_issue(title=f"Low {i}", priority="low")
    closed = create_issue(priority="high")
    assert client.put(f"/issues/{closed['id']}", json={"status": "closed"}).status_code == 200
    response = client.get("/issues", params={
        "status": "open", "priority": "high", "sort_by": "id",
        "sort_order": "desc", "limit": 2, "offset": 1,
    })
    assert response.status_code == 200
    assert [issue["id"] for issue in response.json()] == list(reversed(matching))[1:3]


@pytest.mark.parametrize("params", [
    {"sort_by": "priority"}, {"sort_by": "banana"}, {"sort_order": "random"},
])
def test_invalid_sorting(client, params):
    assert client.get("/issues", params=params).status_code == 422


@pytest.mark.parametrize("params", [{"status": "invalid"}, {"priority": "urgent"}])
def test_invalid_filters(client, params):
    assert client.get("/issues", params=params).status_code == 422
