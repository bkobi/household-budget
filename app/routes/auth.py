from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import get_db
from app.auth_model import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        flash("נא למלא שם משתמש וסיסמה")
        return render_template("login.html"), 400

    conn = get_db()
    row  = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not row or not check_password_hash(row["password_hash"], password):
        flash("שם משתמש או סיסמה שגויים")
        return render_template("login.html"), 401

    login_user(User(row["id"], row["username"]))
    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/setup", methods=["GET"])
def setup_page():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if count > 0:
        return redirect(url_for("auth.login_page"))
    return render_template("setup.html")


@auth_bp.route("/setup", methods=["POST"])
def setup():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if count > 0:
        return redirect(url_for("auth.login_page"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm",  "")

    if not username or not password:
        flash("נא למלא את כל השדות")
        return render_template("setup.html"), 400
    if password != confirm:
        flash("הסיסמאות אינן תואמות")
        return render_template("setup.html"), 400
    if len(password) < 8:
        flash("הסיסמה חייבת להכיל לפחות 8 תווים")
        return render_template("setup.html"), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password))
    )
    conn.commit()
    conn.close()
    return redirect(url_for("auth.login_page"))
