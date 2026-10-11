import os
from datetime import datetime, timezone

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-key-change-before-deployment"
)
if os.environ.get("TASK_MANAGER_TESTING") == "1":
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Сначала войдите в аккаунт."

class RegistrationForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm_password = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired(),
            EqualTo("password", message="Пароли должны совпадать.")
        ]
    )
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired()]
    )
    submit = SubmitField("Войти")


class TaskForm(FlaskForm):
    title = StringField(
        "Название задачи",
        validators=[DataRequired(), Length(max=150)]
    )
    description = TextAreaField("Описание")
    status = SelectField(
        "Статус",
        choices=[
            ("Новая", "Новая"),
            ("В работе", "В работе"),
            ("Завершена", "Завершена")
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Сохранить")

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    tasks = db.relationship(
        "Task", backref="owner", lazy=True, cascade="all, delete-orphan"
    )


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Новая")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("tasks"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("tasks"))

    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        existing_user = db.session.execute(
            db.select(User).where(
                db.or_(User.username == username, User.email == email)
            )
        ).scalar_one_or_none()

        if existing_user:
            flash("Имя пользователя или email уже заняты.", "error")
        else:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(form.password.data)
            )
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Регистрация прошла успешно!", "success")
            return redirect(url_for("tasks"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("tasks"))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for("tasks"))

        flash("Неверный email или пароль.", "error")

    return render_template("login.html", form=form)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("login"))
@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    form = TaskForm()

    if form.validate_on_submit():
        task = Task(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            status=form.status.data,
            user_id=current_user.id
        )

        if not task.title:
            flash("Название задачи не может быть пустым.", "error")
        else:
            db.session.add(task)
            db.session.commit()
            flash("Задача успешно создана.", "success")
            return redirect(url_for("tasks"))

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    query = db.select(Task).where(Task.user_id == current_user.id)

    if search:
        query = query.where(
            db.or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%")
            )
        )

    if status in ("Новая", "В работе", "Завершена"):
        query = query.where(Task.status == status)

    task_list = db.session.execute(
        query.order_by(Task.created_at.desc())
    ).scalars().all()

    return render_template(
        "tasks.html",
        form=form,
        tasks=task_list,
        search=search,
        selected_status=status
    )

@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = db.get_or_404(Task, task_id)

    if task.user_id != current_user.id:
        flash("У вас нет доступа к этой задаче.", "error")
        return redirect(url_for("tasks"))

    form = TaskForm(obj=task)

    if form.validate_on_submit():
        title = form.title.data.strip()

        if not title:
            flash("Название задачи не может быть пустым.", "error")
        else:
            task.title = title
            task.description = form.description.data.strip()
            task.status = form.status.data
            db.session.commit()

            flash("Задача обновлена.", "success")
            return redirect(url_for("tasks"))

    return render_template("edit_task.html", form=form, task=task)


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)

    if task.user_id != current_user.id:
        flash("У вас нет доступа к этой задаче.", "error")
        return redirect(url_for("tasks"))

    db.session.delete(task)
    db.session.commit()

    flash("Задача удалена.", "success")
    return redirect(url_for("tasks"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=False)