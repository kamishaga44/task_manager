# Task Manager

A web application for managing personal tasks, built with Python and Flask.

## Features

- User registration and login
- Password hashing
- Create, view, edit, and delete tasks
- Task status management
- Search tasks by title or description
- Filter tasks by status
- User-specific task access
- Form validation and CSRF protection
- SQLite database

## Technologies

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- SQLite
- pytest

## Project Structure

```text
task_manager/
├── app.py
├── test_app.py
├── requirements.txt
├── README.md
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── login.html
    ├── register.html
    ├── tasks.html
    └── edit_task.html
```

## Installation and Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/kamishaga44/task_manager.git
   cd task_manager
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5000` in your browser.

## Running Tests

Run the automated tests with:

```bash
pytest -v
```

## Security

- Passwords are stored as hashes.
- Login is required to access personal tasks.
- Users cannot edit or delete tasks belonging to other users.
- Forms use CSRF protection.
- Input validation is applied to user-submitted data.

## Purpose

This project demonstrates basic web development, database operations, authentication, CRUD functionality, input validation, and automated testing.
