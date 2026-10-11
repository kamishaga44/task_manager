import os

os.environ["TASK_MANAGER_TESTING"] = "1"

import pytest

from app import app, db, User, Task
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False


    with app.app_context():
        db.drop_all()
        db.create_all()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("testpassword123"),
        )
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=generate_password_hash("otherpassword123"),
        )

        db.session.add_all([user, other_user])
        db.session.commit()

        task = Task(
            title="Тестовая задача",
            description="Описание задачи",
            status="Новая",
            user_id=other_user.id,
        )
        db.session.add(task)
        db.session.commit()

        task_id = task.id
        other_user_id = other_user.id
        db.session.commit()

        with app.test_client() as test_client:
            with test_client.session_transaction() as session:
                session["_user_id"] = str(user.id)
                session["_fresh"] = True

            yield test_client, task_id, other_user_id

        db.session.remove()
        db.drop_all()


def test_home_redirects_to_login_when_logged_out():
    with app.test_client() as test_client:
        response = test_client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location


def test_login_page_opens():
    with app.test_client() as test_client:
        response = test_client.get("/login")
        assert response.status_code == 200


def test_register_page_opens():
    with app.test_client() as test_client:
        response = test_client.get("/register")
        assert response.status_code == 200


def test_logged_in_user_can_open_tasks(client):
    test_client, _, _ = client
    response = test_client.get("/tasks")
    assert response.status_code == 200


def test_user_cannot_edit_another_users_task(client):
    test_client, task_id, _ = client
    response = test_client.get(f"/tasks/{task_id}/edit")
    assert response.status_code == 302
    assert "/tasks" in response.location


def test_user_cannot_delete_another_users_task(client):
    test_client, task_id, _ = client
    response = test_client.post(f"/tasks/{task_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task is not None


def test_task_page_requires_login():
    with app.test_client() as test_client:
        response = test_client.get("/tasks")
        assert response.status_code == 302
        assert "/login" in response.location