import os
import re
import io
import math
import uuid
import hashlib
import random
import mimetypes
import urllib.parse
from werkzeug.routing import BaseConverter
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from flask import (
    Flask, render_template, request, redirect,
    url_for, make_response, send_from_directory, flash, abort
)

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
UPLOAD_FOLDER      = os.getenv("UPLOAD_FOLDER", "data")
SALT               = os.getenv("SALT")
VALID_USERNAME     = os.getenv("VALID_USERNAME")
VALID_PASSWORD     = os.getenv("VALID_PASSWORD")
COOKIE_NAME        = os.getenv("COOKIE_NAME")
COOKIE_TIMEOUT     = int(os.getenv("COOKIE_TIMEOUT", "300"))
HOST               = os.getenv("HOST", "0.0.0.0")
PORT               = int(os.getenv("PORT", "3001"))
FLASK_DEBUG        = os.getenv("FLASK_DEBUG", "false").lower() == "true"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
TOP_SITES          = ['https://example.com', 'https://github.com', 'https://google.com']

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])


class RegexConverter(BaseConverter):
    def __init__(self, map, *args):
        super().__init__(map)
        self.regex = args[0]

app.url_map.converters["regex"] = RegexConverter

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def index():
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return redirect(url_for("login"))
    try:
        username, password = serializer.loads(cookie, salt=SALT, max_age=COOKIE_TIMEOUT).split("|")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            return redirect(url_for("main"))
    except (BadSignature, SignatureExpired):
        pass
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    show_main = False
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == VALID_USERNAME and p == VALID_PASSWORD:
            payload = f"{u}|{p}"
            signed = serializer.dumps(payload, salt=SALT)
            resp = make_response(redirect(url_for("main")))
            resp.set_cookie(COOKIE_NAME, signed,
                            max_age=COOKIE_TIMEOUT, httponly=True)
            return resp
        error = "Invalid credentials"
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        try:
            u, p = serializer.loads(cookie, salt=SALT, max_age=COOKIE_TIMEOUT).split("|")
            show_main = (u == VALID_USERNAME and p == VALID_PASSWORD)
        except (BadSignature, SignatureExpired):
            pass
    return render_template("login.html", error=error, show_main_button=show_main)

@app.route("/main")
def main():
    cookie = request.cookies.get(COOKIE_NAME)
    try:
        user, pwd = serializer.loads(cookie, salt=SALT, max_age=COOKIE_TIMEOUT).split("|")
        if user != VALID_USERNAME or pwd != VALID_PASSWORD:
            return redirect(url_for("login"))
    except Exception:
        return redirect(url_for("login"))
    page_str = request.args.get("page", "1")
    if not re.fullmatch(r"\d+", page_str):
        page = 1
    else:
        page = max(1, int(page_str))
    files = sorted(f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.endswith(".png"))
    ids = [fname[:-4] for fname in files]
    total = len(ids)
    total_pages = max(1, math.ceil(total / 9))
    page = min(page, total_pages)
    start = (page - 1) * 9
    page_ids = ids[start : start + 9]
    page_ids += [None] * (9 - len(page_ids))
    grid = [page_ids[i * 3 : (i + 1) * 3] for i in range(3)]
    return render_template("main.html", image_grid=grid, page=page, total_pages=total_pages)

@app.route("/upload", methods=["POST"])
def upload():
    cookie = request.cookies.get(COOKIE_NAME)
    try:
        user, pwd = serializer.loads(cookie, salt=SALT, max_age=COOKIE_TIMEOUT).split("|")
        if user != VALID_USERNAME or pwd != VALID_PASSWORD:
            return redirect(url_for("login"))
    except Exception:
        return redirect(url_for("login"))
    file = request.files.get("image")
    if not file or not allowed_file(file.filename):
        return render_template("main.html", error="File extension not allowed")
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type not in ALLOWED_MIME_TYPES:
        return render_template("main.html", error="Unsupported image MIME type")
    data = file.read()
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except (UnidentifiedImageError, OSError):
        return render_template("main.html", error="Invalid image file")
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img.info.pop("exif", None)
    img.info.pop("icc_profile", None)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=9)
    png = buf.getvalue()
    md5 = hashlib.md5(png).hexdigest()
    unique_id = str(uuid.UUID(md5))
    fname = f"{unique_id}.png"
    path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    with open(path, "wb") as f:
        f.write(png)
    return redirect(url_for("main"))

@app.route('/delete', methods=['POST'])
def delete():
    image_ids = request.form.getlist('delete_ids')
    if not image_ids:
        flash('No images selected for deletion.', 'warning')
        return redirect(url_for('main'))
    deleted = 0
    for img_id in image_ids:
        safe_id  = secure_filename(img_id)
        filename = f"{safe_id}.png"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            os.remove(path)
            deleted += 1
    flash(f'Deleted {deleted} image(s).', 'success')
    return redirect(url_for('main'))

@app.route("/<uuid:image_id>.png")
def serve_image(image_id):
    fname = f"{image_id}.png"
    folder = app.config["UPLOAD_FOLDER"]
    if os.path.isfile(os.path.join(folder, fname)):
        return send_from_directory(folder, fname, mimetype="image/png")
    return redirect(random.choice(TOP_SITES), code=302)

@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie(COOKIE_NAME)
    return resp

@app.route('/<path:any_path>')
def catch_all(any_path):
    target = random.choice(TOP_SITES)
    resp = make_response(redirect(target, 302))
    resp.headers['Referrer-Policy'] = 'no-referrer'
    return resp

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host=HOST, port=PORT, debug=FLASK_DEBUG, use_reloader=FLASK_DEBUG)
