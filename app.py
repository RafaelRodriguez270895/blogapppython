import os
import random
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------
# App config (old-school)
# -----------------------
# "Hace 10 años": Flask + Jinja + SQLAlchemy, templates simples, sin SPA.
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")  # demo
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:////data/blog.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------
# Models
# -----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship("Comment", backref="post", cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------
# Helpers
# -----------------------
def is_logged_in():
    return bool(session.get("user_id"))

def require_login():
    if not is_logged_in():
        abort(403)

def simple_slugify(s):
    # "De hace 10 años": slugify simple y casero (no perfecto)
    s = (s or "").strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in [" ", "-", "_"]:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "post"

def get_latest_posts(limit=6):
    return Post.query.order_by(Post.created_at.desc()).limit(limit).all()

def excerpt(text, n=240):
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "..."

# Make excerpt available in templates
app.jinja_env.globals.update(excerpt=excerpt)

# -----------------------
# CLI: init / seed
# -----------------------
@app.cli.command("initdb")
def initdb():
    """Create tables + seed admin and sample post if empty."""
    os.makedirs("/data", exist_ok=True)
    db.create_all()

    # create admin user if none
    if not User.query.filter_by(username="admin").first():
        pw = os.environ.get("ADMIN_PASSWORD", "admin123")
        u = User(username="admin", password_hash=generate_password_hash(pw))
        db.session.add(u)
        db.session.commit()
        print("Created admin user: admin")
        print("Admin password (from env ADMIN_PASSWORD or default):", pw)

    # sample post if none
    if Post.query.count() == 0:
        p = Post(
            title="Hola mundo (demo blog)",
            slug="hola-mundo",
            content="Este es un post de ejemplo. Edita, crea más y prueba comentarios."
        )
        db.session.add(p)
        db.session.commit()
        print("Seeded sample post.")

LOREM = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor.",
    "Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet.",
    "Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa.",
    "Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos.",
    "Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh.",
    "Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis tristique sem.",
]
TITLE_WORDS = ["Rails", "Docker", "Seguridad", "Logs", "Nginx", "AWS", "Kali", "PKI", "TLS", "DevOps", "Auditoría", "Hardening", "Backups", "CI/CD"]

def rand_title():
    a = random.choice(TITLE_WORDS)
    b = random.choice(TITLE_WORDS)
    c = random.choice(TITLE_WORDS)
    return f"{a}: {b} y {c}"

def rand_body(paragraphs=6):
    return "\n\n".join(random.choice(LOREM) for _ in range(paragraphs))

@app.cli.command("seed")
def seed():
    """Seed posts + comments if DB is almost empty."""
    os.makedirs("/data", exist_ok=True)
    db.create_all()

    if Post.query.count() > 3:
        print("Seed skipped (already has data).")
        return

    # create a few extra posts
    for i in range(12):
        title = rand_title()
        slug = simple_slugify(title)

        # ensure unique slug
        base = slug
        n = 2
        while Post.query.filter_by(slug=slug).first():
            slug = f"{base}-{n}"
            n += 1

        p = Post(
            title=title,
            slug=slug,
            content=rand_body(paragraphs=random.randint(4, 9)),
            created_at=datetime.utcnow(),
        )
        db.session.add(p)
        db.session.flush()

        # 0-6 comments per post
        for _ in range(random.randint(0, 6)):
            c = Comment(
                post_id=p.id,
                author=random.choice(["Ana", "Luis", "Carlos", "María", "DevOpsBot", "Guest", "Admin"]),
                body=rand_body(paragraphs=random.randint(1, 2)),
            )
            db.session.add(c)

    db.session.commit()
    print("Seeded posts and comments.")

# -----------------------
# Routes (public)
# -----------------------
@app.route("/")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    latest = get_latest_posts()
    return render_template("index.html", posts=posts, latest=latest)

@app.route("/p/<slug>", methods=["GET", "POST"])
def post_view(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()

    if request.method == "POST":
        author = (request.form.get("author") or "").strip()
        body = (request.form.get("body") or "").strip()
        if not author or not body:
            flash("Nombre y comentario son obligatorios.", "error")
            return redirect(url_for("post_view", slug=slug))

        c = Comment(post_id=post.id, author=author, body=body)
        db.session.add(c)
        db.session.commit()
        flash("Comentario publicado.", "ok")
        return redirect(url_for("post_view", slug=slug))

    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.asc()).all()
    latest = get_latest_posts()
    return render_template("post.html", post=post, comments=comments, latest=latest)

# -----------------------
# Auth
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        u = User.query.filter_by(username=username).first()
        if u and check_password_hash(u.password_hash, password):
            session["user_id"] = u.id
            flash("Login OK.", "ok")
            return redirect(url_for("admin"))
        flash("Credenciales inválidas.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("index"))

# -----------------------
# Admin CRUD
# -----------------------
@app.route("/admin")
def admin():
    require_login()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin.html", posts=posts)

@app.route("/admin/new", methods=["GET", "POST"])
def new_post():
    require_login()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        slug = simple_slugify(request.form.get("slug") or title)

        if not title or not content:
            flash("Título y contenido son obligatorios.", "error")
            return redirect(url_for("new_post"))

        # ensure unique slug
        base = slug
        i = 2
        while Post.query.filter_by(slug=slug).first():
            slug = f"{base}-{i}"
            i += 1

        p = Post(title=title, slug=slug, content=content)
        db.session.add(p)
        db.session.commit()
        flash("Post creado.", "ok")
        return redirect(url_for("admin"))

    return render_template("edit.html", mode="new", post=None)

@app.route("/admin/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    require_login()
    post = Post.query.get_or_404(post_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        slug = simple_slugify(request.form.get("slug") or title)

        if not title or not content:
            flash("Título y contenido son obligatorios.", "error")
            return redirect(url_for("edit_post", post_id=post.id))

        # unique slug (excluding current)
        if slug != post.slug and Post.query.filter_by(slug=slug).first():
            flash("Ese slug ya existe. Usa otro.", "error")
            return redirect(url_for("edit_post", post_id=post.id))

        post.title = title
        post.slug = slug
        post.content = content
        db.session.commit()
        flash("Post actualizado.", "ok")
        return redirect(url_for("admin"))

    return render_template("edit.html", mode="edit", post=post)

@app.route("/admin/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    require_login()
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post eliminado.", "ok")
    return redirect(url_for("admin"))

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
