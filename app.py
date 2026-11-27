import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "news.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("BAHRAMAH_SECRET") or secrets.token_hex(32)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    db = get_db()
    news = db.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()
    db.close()
    return render_template("index.html", news=news)


@app.route("/news/<int:news_id>")
def news_detail(news_id):
    db = get_db()
    article = db.execute(
        "SELECT * FROM news WHERE id = ?", (news_id,)
    ).fetchone()
    db.close()

    if article is None:
        return "الخبر غير موجود", 404

    return render_template("article.html", article=article)


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["admin_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("dashboard"))

        flash("اسم المستخدم أو كلمة المرور غير صحيحة")

    return render_template("login.html")


@app.route("/admin/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def dashboard():
    db = get_db()
    news = db.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()
    db.close()
    return render_template("dashboard.html", news=news)


@app.route("/admin/news/add", methods=["GET", "POST"])
@admin_required
def add_news():
    if request.method == "POST":
        if request.form.get("csrf_token") != session.get("csrf_token"):
            return "طلب غير صالح", 400

        title = request.form.get("title", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "").strip()

        if not all([title, summary, content, category]):
            flash("يرجى ملء جميع الحقول")
            return redirect(url_for("add_news"))

        if len(title) > 200 or len(summary) > 500:
            flash("العنوان أو الملخص طويل جداً")
            return redirect(url_for("add_news"))

        image_name = None
        image = request.files.get("image")

        if image and image.filename:
            if not allowed_file(image.filename):
                flash("صيغة الصورة غير مسموح بها")
                return redirect(url_for("add_news"))

            image_name = secrets.token_hex(16) + "." + image.filename.rsplit(".", 1)[1].lower()
            image.save(os.path.join(UPLOAD_FOLDER, image_name))

        db = get_db()
        db.execute(
            """INSERT INTO news
            (title, summary, content, category, image, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                title, summary, content, category,
                image_name, datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )
        db.commit()
        db.close()

        flash("تم نشر الخبر بنجاح")
        return redirect(url_for("dashboard"))

    return render_template("add_news.html")


@app.route("/admin/news/delete/<int:news_id>", methods=["POST"])
@admin_required
def delete_news(news_id):
    if request.form.get("csrf_token") != session.get("csrf_token"):
        return "طلب غير صالح", 400

    db = get_db()
    article = db.execute(
        "SELECT image FROM news WHERE id = ?", (news_id,)
    ).fetchone()

    if article:
        if article["image"]:
            path = os.path.join(UPLOAD_FOLDER, article["image"])
            if os.path.isfile(path):
                os.remove(path)

        db.execute("DELETE FROM news WHERE id = ?", (news_id,))
        db.commit()

    db.close()
    flash("تم حذف الخبر")
    return redirect(url_for("dashboard"))


@app.errorhandler(413)
def too_large(error):
    return "حجم الصورة أكبر من الحد المسموح (5 ميغابايت)", 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8081, debug=False)
