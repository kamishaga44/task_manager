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



def test_user_can_register_successfully(client):
    test_client, _, _ = client

    with test_client.session_transaction() as session:
        session.clear()

    test_client.get("/register")

    response = test_client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "confirm_password": "newpassword123",
            "submit": "Зарегистрироваться",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


    with app.app_context():
        user = db.session.execute(
            db.select(User).where(User.email == "newuser@example.com")
        ).scalar_one_or_none()

        assert user is not None
        assert user.username == "newuser"
        assert user.password_hash != "newpassword123"

def test_user_can_create_task(client):
    test_client, _, _ = client

    response = test_client.post(
        "/tasks",
        data={
            "title": "Подготовить резюме",
            "description": "Добавить проекты в портфолио",
            "status": "Новая",
            "submit": "Сохранить",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = db.session.execute(
            db.select(User).where(User.username == "testuser")
        ).scalar_one()

        task = db.session.execute(
            db.select(Task).where(
                Task.title == "Подготовить резюме",
                Task.user_id == user.id,
            )
        ).scalar_one_or_none()

        assert task is not None
        assert task.description == "Добавить проекты в портфолио"
        assert task.status == "Новая"

def test_user_can_edit_own_task(client):
    test_client, _, _ = client

    with app.app_context():
        user = db.session.execute(
            db.select(User).where(User.username == "testuser")
        ).scalar_one()

        task = Task(
            title="Моя тестовая задача",
            description="Исходное описание",
            status="Новая",
            user_id=user.id,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = test_client.post(
        f"/tasks/{task_id}/edit",
        data={
            "title": "Обновлённая задача",
            "description": "Новое описание",
            "status": "В работе",
            "submit": "Сохранить",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task is not None
        assert task.title == "Обновлённая задача"
        assert task.description == "Новое описание"
        assert task.status == "В работе"

def test_user_can_delete_own_task(client):
    test_client, _, _ = client

    with app.app_context():
        user = db.session.execute(
            db.select(User).where(User.username == "testuser")
        ).scalar_one()

        task = Task(
            title="Моя тестовая задача",
            description="Исходное описание",
            status="Новая",
            user_id=user.id,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = test_client.post(
        f"/tasks/{task_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task is None

def test_user_cannot_create_task_with_blank_title(client):
    test_client, _, _ = client

    with app.app_context():
        before_count = db.session.query(Task).count()

    response = test_client.post(
        "/tasks",
        data={
            "title": "   ",
            "description": "Описание",
            "status": "Новая",
            "submit": "Сохранить",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        after_count = db.session.query(Task).count()
        assert after_count == before_count


def test_user_cannot_create_task_with_invalid_status(client):
    test_client, _, _ = client

    with app.app_context():
        before_count = db.session.query(Task).count()

    response = test_client.post(
        "/tasks",
        data={
            "title": "Проверка статуса",
            "description": "Тест недопустимого статуса",
            "status": "Удалена",
            "submit": "Сохранить",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        after_count = db.session.query(Task).count()
        assert after_count == before_count


def test_user_cannot_register_with_short_password(client):
    test_client, _, _ = client

    with test_client.session_transaction() as session:
        session.clear()

    response = test_client.post(
        "/register",
        data={
            "username": "shortpassuser",
            "email": "shortpass@example.com",
            "password": "123",
            "confirm_password": "123",
            "submit": "Зарегистрироваться",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = db.session.execute(
            db.select(User).where(
                User.email == "shortpass@example.com"
            )
        ).scalar_one_or_none()

        assert user is None

def test_user_cannot_register_with_mismatched_passwords(client):
    test_client, _, _ = client

    with test_client.session_transaction() as session:
        session.clear()

    response = test_client.post(
        "/register",
        data={
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "different123",
            "submit": "Зарегистрироваться",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = db.session.execute(
            db.select(User).where(
                User.email == "mismatch@example.com"
            )
        ).scalar_one_or_none()

        assert user is None

def test_user_cannot_login_with_wrong_password(client):
    test_client, _, _ = client

    with test_client.session_transaction() as session:
        session.clear()

    response = test_client.post(
        "/login",
        data={
            "email": "test@example.com",
            "password": "wrongpassword123",
            "submit": "Войти",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_client.session_transaction() as session:
        assert "_user_id" not in session




def test_login_rejects_request_without_csrf_token():
    original_csrf = app.config["WTF_CSRF_ENABLED"]
    original_testing = app.config["TESTING"]

    try:
        app.config["WTF_CSRF_ENABLED"] = True
        app.config["TESTING"] = False

        with app.test_client() as test_client:
            response = test_client.post(
                "/login",
                data={
                    "email": "test@example.com",
                    "password": "testpassword123",
                    "submit": "Войти",
                },
            )

        assert response.status_code == 400

    finally:
        app.config["WTF_CSRF_ENABLED"] = original_csrf
        app.config["TESTING"] = original_testing
