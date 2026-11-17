"""उधारी खाते – किराणा दुकानासाठी उधारी व्यवस्थापन (Flask PWA, मराठी)

DATABASE_URL  -> Supabase Postgres (pooler) connection string. Not set -> local SQLite file.
"""
import csv
import io
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import quote, urlparse

from flask import (Flask, Response, abort, flash, jsonify, redirect,
                   render_template, request, send_from_directory, session,
                   url_for)
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup
from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IST = timezone(timedelta(hours=5, minutes=30))
ASSET_VERSION = "2"  # वाढवा म्हणजे CSS/JS बदल फोनवर लगेच दिसतात

MONTHS_MR = ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून",
             "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
MAX_PAISE = 10 ** 11  # ₹100 कोटी पेक्षा जास्त नको


def today_ist():
    return datetime.now(IST).date()


# --------------------------------------------------------------------------
# App + config
# --------------------------------------------------------------------------
def database_uri():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
        return "sqlite:///" + os.path.join(BASE_DIR, "instance", "udhari.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

IS_PROD = bool(os.environ.get("RENDER")) or os.environ.get("FLASK_ENV") == "production"
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SQLALCHEMY_DATABASE_URI=database_uri(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PROD,
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    MAX_CONTENT_LENGTH=1024 * 1024,
)
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 3,
        "max_overflow": 2,
        "connect_args": {"sslmode": os.environ.get("DB_SSLMODE", "require")},
    }

SHOP_NAME = os.environ.get("SHOP_NAME", "किराणा दुकान")
db = SQLAlchemy(app)


# --------------------------------------------------------------------------
# Models  (रक्कम paise मध्ये साठवतो – दशांश चुका टाळण्यासाठी)
# --------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(10))  # १० अंकी, प्रत्येक ग्राहकाला वेगळा (unique index खाली)
    address = db.Column(db.String(200))
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    entries = db.relationship("Entry", backref="customer", cascade="all, delete-orphan",
                              passive_deletes=False, lazy="dynamic")
    __table_args__ = (db.Index("uq_customers_phone", "phone", unique=True),)


class Entry(db.Model):
    __tablename__ = "entries"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    kind = db.Column(db.String(10), nullable=False)  # 'credit' = उधार, 'payment' = जमा
    amount_paise = db.Column(db.BigInteger, nullable=False)
    entry_date = db.Column(db.Date, nullable=False, default=today_ist, index=True)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def signed(self):
        return self.amount_paise if self.kind == "credit" else -self.amount_paise


# --------------------------------------------------------------------------
# Template helpers
# --------------------------------------------------------------------------
def inr(paise, plain=False):
    paise = int(paise or 0)
    neg = paise < 0
    paise = abs(paise)
    whole, frac = str(paise // 100), paise % 100
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    out = whole + (".%02d" % frac if frac else "")
    return ("-" if neg else "") + ("" if plain else "₹") + out


def mdate(d, short=False):
    if not d:
        return ""
    if short:
        return "%d %s %d" % (d.day, MONTHS_MR[d.month - 1][:3], d.year)
    return "%d %s %d" % (d.day, MONTHS_MR[d.month - 1], d.year)


def amt_input(paise):
    """paise -> '1250' / '1250.5' / '1250.05' for the amount input box."""
    return inr(paise, plain=True).replace(",", "") if paise else ""


app.jinja_env.filters["inr"] = inr
app.jinja_env.filters["mdate"] = mdate
app.jinja_env.filters["amt"] = amt_input


@app.context_processor
def inject_globals():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {
        "shop_name": SHOP_NAME,
        "csrf_token": session["csrf"],
        "logged_in": bool(session.get("uid")),
        "asset_v": ASSET_VERSION,
        "today_label": mdate(today_ist()),
    }


# --------------------------------------------------------------------------
# Security: CSRF, login, throttle
# --------------------------------------------------------------------------
@app.before_request
def csrf_protect():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            flash("सुरक्षा तपासणी अयशस्वी. कृपया पान रिफ्रेश करून पुन्हा प्रयत्न करा.", "error")
            return redirect(request.referrer or url_for("login"))


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.endpoint not in ("static", "manifest", "service_worker"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not session.get("uid"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


_FAILS = {}  # ip -> [count, first_ts]
MAX_FAILS, WINDOW = 6, 600


def _blocked(ip):
    rec = _FAILS.get(ip)
    if not rec:
        return False
    if time.time() - rec[1] > WINDOW:
        _FAILS.pop(ip, None)
        return False
    return rec[0] >= MAX_FAILS


def _fail(ip):
    rec = _FAILS.get(ip)
    if not rec or time.time() - rec[1] > WINDOW:
        _FAILS[ip] = [1, time.time()]
    else:
        rec[0] += 1


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") \
            and not urlparse(target).netloc:
        return target
    return url_for("dashboard")


# --------------------------------------------------------------------------
# Input parsing
# --------------------------------------------------------------------------
_DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")


def parse_amount(raw):
    """'1,250.50' / '१२५०' -> paise (int) or None."""
    s = (raw or "").translate(_DEVANAGARI).replace(",", "").replace("₹", "").strip()
    if not s:
        return None
    try:
        if "." in s:
            whole, frac = s.split(".", 1)
            if not (whole or frac) or not (whole + frac).isdigit() or len(frac) > 2:
                return None
            paise = int(whole or "0") * 100 + int((frac + "00")[:2])
        else:
            if not s.isdigit():
                return None
            paise = int(s) * 100
    except ValueError:
        return None
    return paise if 0 < paise < MAX_PAISE else None


def parse_date(raw):
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_phone(raw):
    """फक्त १० अंक स्वीकारतो (मराठी अंक चालतील, स्पेस/'-' काढले जातात). अन्यथा None."""
    s = re.sub(r"[\s\-]", "", (raw or "").translate(_DEVANAGARI))
    return s if len(s) == 10 and s.isascii() and s.isdigit() else None


app.jinja_env.globals["ic"] = lambda name, cls="": Markup(
    '<svg class="ic %s" aria-hidden="true"><use href="#i-%s"/></svg>' % (cls, name))


def balance_expr():
    return func.coalesce(func.sum(case((Entry.kind == "credit", Entry.amount_paise),
                                       else_=-Entry.amount_paise)), 0)


def customers_with_balance():
    bal = balance_expr().label("balance")
    return (db.session.query(Customer, bal)
            .outerjoin(Entry, Entry.customer_id == Customer.id)
            .group_by(Customer.id), bal)


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("uid"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if _blocked(ip):
            flash("खूप चुकीचे प्रयत्न झाले. १० मिनिटांनी पुन्हा प्रयत्न करा.", "error")
            return render_template("login.html"), 429
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            _FAILS.pop(ip, None)
            session.clear()
            session.permanent = True
            session["uid"] = user.id
            session["csrf"] = secrets.token_hex(16)
            return redirect(safe_next(request.args.get("next")))
        _fail(ip)
        flash("वापरकर्ता नाव किंवा पासवर्ड चुकीचा आहे.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("तुम्ही बाहेर पडलात.", "success")
    return redirect(url_for("login"))


@app.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        user = db.session.get(User, session["uid"])
        old, new, again = (request.form.get(k, "") for k in ("old", "new", "again"))
        if not check_password_hash(user.password_hash, old):
            flash("सध्याचा पासवर्ड चुकीचा आहे.", "error")
        elif len(new) < 6:
            flash("नवीन पासवर्ड किमान ६ अक्षरांचा असावा.", "error")
        elif new != again:
            flash("नवीन पासवर्ड दोन्ही ठिकाणी सारखा नाही.", "error")
        else:
            user.password_hash = generate_password_hash(new)
            db.session.commit()
            flash("पासवर्ड बदलला गेला.", "success")
            return redirect(url_for("dashboard"))
    return render_template("password.html")


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    today = today_ist()
    base, bal = customers_with_balance()
    total_due = db.session.query(balance_expr()).select_from(Entry).scalar() or 0
    due_count = base.having(bal > 0).count()
    top_dues = base.having(bal > 0).order_by(bal.desc()).limit(5).all()

    def day_sum(kind):
        return (db.session.query(func.coalesce(func.sum(Entry.amount_paise), 0))
                .filter(Entry.kind == kind, Entry.entry_date == today).scalar())

    recent = (Entry.query.join(Customer)
              .order_by(Entry.created_at.desc(), Entry.id.desc()).limit(8).all())
    return render_template(
        "dashboard.html", total_due=total_due, due_count=due_count,
        customer_total=Customer.query.count(), top_dues=top_dues,
        today_credit=day_sum("credit"), today_payment=day_sum("payment"), recent=recent)


# --------------------------------------------------------------------------
# Customers
# --------------------------------------------------------------------------
@app.route("/customers")
@login_required
def customers():
    q = request.args.get("q", "").strip()
    only_due = request.args.get("f") == "due"
    base, bal = customers_with_balance()
    if q:
        like = "%" + q.replace("%", "").replace("_", "") + "%"
        base = base.filter(or_(Customer.name.ilike(like), Customer.phone.like(like)))
    if only_due:
        base = base.having(bal > 0).order_by(bal.desc(), Customer.name)
    else:
        base = base.order_by(Customer.name)
    return render_template("customers.html", rows=base.all(), q=q, only_due=only_due)


DUP_MSG = "हा मोबाईल नंबर आधीच “%s” या ग्राहकासाठी नोंदवलेला आहे. प्रत्येक ग्राहकाचा नंबर वेगळा हवा."


def _customer_from_form(c):
    name = request.form.get("name", "").strip()
    phone = parse_phone(request.form.get("phone"))
    if not name:
        flash("ग्राहकाचे नाव आवश्यक आहे.", "error")
        return False
    if not phone:
        flash("मोबाईल नंबर आवश्यक आहे आणि तो अचूक १० अंकी असावा.", "error")
        return False
    other = Customer.query.filter(Customer.phone == phone, Customer.id != (c.id or 0)).first()
    if other:
        flash(DUP_MSG % other.name, "error")
        return False
    c.name = name[:100]
    c.phone = phone
    c.address = request.form.get("address", "").strip()[:200] or None
    c.note = request.form.get("note", "").strip()[:200] or None
    return True


def _commit_customer(c):
    """commit करतो; दोन जणांनी एकाच वेळी तोच नंबर टाकला तरी DB unique index अडवतो."""
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        flash(DUP_MSG % "दुसरा ग्राहक", "error")
        return False


@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():
    c = Customer()
    if request.method == "POST" and _customer_from_form(c):
        db.session.add(c)
        if _commit_customer(c):
            flash("ग्राहक जोडला: %s" % c.name, "success")
            return redirect(url_for("customer_detail", cid=c.id))
        c = Customer()
    return render_template("customer_form.html", c=c, form=request.form, is_new=True)


@app.route("/customers/<int:cid>")
@login_required
def customer_detail(cid):
    c = db.get_or_404(Customer, cid)
    entries = c.entries.order_by(Entry.entry_date, Entry.id).all()
    running, rows = 0, []
    for e in entries:
        running += e.signed
        rows.append((e, running))
    rows.reverse()  # नवीन नोंदी वर
    total_credit = sum(e.amount_paise for e in entries if e.kind == "credit")
    total_paid = sum(e.amount_paise for e in entries if e.kind == "payment")
    balance = total_credit - total_paid
    wa = None
    if c.phone and balance > 0:
        msg = ("नमस्कार %s, %s मधील आपला बाकी हिशोब %s आहे. "
               "कृपया सवडीने जमा करावा. धन्यवाद 🙏") % (c.name, SHOP_NAME, inr(balance))
        wa = "https://wa.me/91%s?text=%s" % (c.phone, quote(msg))
    return render_template("customer_detail.html", c=c, rows=rows, balance=balance,
                           total_credit=total_credit, total_paid=total_paid, wa=wa)


@app.route("/customers/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(cid):
    c = db.get_or_404(Customer, cid)
    if request.method == "POST" and _customer_from_form(c):
        if _commit_customer(c):
            flash("ग्राहकाची माहिती बदलली.", "success")
            return redirect(url_for("customer_detail", cid=c.id))
    db.session.rollback()
    c = db.get_or_404(Customer, cid)
    return render_template("customer_form.html", c=c, form=request.form, is_new=False)


@app.route("/customers/<int:cid>/delete", methods=["POST"])
@login_required
def customer_delete(cid):
    c = db.get_or_404(Customer, cid)
    name = c.name
    db.session.delete(c)
    db.session.commit()
    flash("ग्राहक व त्याच्या सर्व नोंदी काढल्या: %s" % name, "success")
    return redirect(url_for("customers"))


# --------------------------------------------------------------------------
# Entries
# --------------------------------------------------------------------------
def _entry_from_form(e):
    kind = request.form.get("kind")
    amount = parse_amount(request.form.get("amount"))
    when = parse_date(request.form.get("entry_date")) or None
    if kind not in ("credit", "payment"):
        flash("नोंदीचा प्रकार निवडा.", "error")
    elif amount is None:
        flash("योग्य रक्कम टाका (० पेक्षा जास्त).", "error")
    elif when is None:
        flash("योग्य तारीख निवडा.", "error")
    else:
        e.kind, e.amount_paise, e.entry_date = kind, amount, when
        e.note = request.form.get("note", "").strip()[:200] or None
        return True
    return False


@app.route("/customers/<int:cid>/entry/new", methods=["GET", "POST"])
@login_required
def entry_new(cid):
    c = db.get_or_404(Customer, cid)
    e = Entry(customer_id=c.id, kind=request.args.get("kind", "credit"), entry_date=today_ist())
    if e.kind not in ("credit", "payment"):
        e.kind = "credit"
    if request.method == "POST" and _entry_from_form(e):
        db.session.add(e)
        db.session.commit()
        flash(("उधार नोंदवला: " if e.kind == "credit" else "जमा नोंदवले: ") + inr(e.amount_paise),
              "success")
        return redirect(url_for("customer_detail", cid=c.id))
    return render_template("entry_form.html", c=c, e=e, form=request.form, is_new=True)


@app.route("/entries/<int:eid>/edit", methods=["GET", "POST"])
@login_required
def entry_edit(eid):
    e = db.get_or_404(Entry, eid)
    if request.method == "POST" and _entry_from_form(e):
        db.session.commit()
        flash("नोंद बदलली.", "success")
        return redirect(url_for("customer_detail", cid=e.customer_id))
    db.session.rollback()
    return render_template("entry_form.html", c=e.customer, e=e, form=request.form, is_new=False)


@app.route("/entries/<int:eid>/delete", methods=["POST"])
@login_required
def entry_delete(eid):
    e = db.get_or_404(Entry, eid)
    cid = e.customer_id
    db.session.delete(e)
    db.session.commit()
    flash("नोंद काढली.", "success")
    return redirect(url_for("customer_detail", cid=cid))


# --------------------------------------------------------------------------
# बाकी यादी (CSV) – Excel मध्ये उघडता येते
# --------------------------------------------------------------------------
@app.route("/export/dues.csv")
@login_required
def export_dues():
    base, bal = customers_with_balance()
    out = io.StringIO()
    out.write("﻿")  # Excel ला मराठी (UTF-8) ओळखण्यासाठी
    w = csv.writer(out)
    w.writerow(["नाव", "मोबाईल", "पत्ता", "बाकी रक्कम (₹)"])
    for c, b in base.having(bal > 0).order_by(bal.desc()).all():
        w.writerow([c.name, c.phone or "", c.address or "", inr(b, plain=True).replace(",", "")])
    return Response(out.getvalue(), mimetype="text/csv; charset=utf-8", headers={
        "Content-Disposition": "attachment; filename=baki-yadi-%s.csv" % today_ist().isoformat()})


# --------------------------------------------------------------------------
# PWA + health
# --------------------------------------------------------------------------
@app.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "%s – उधारी खाते" % SHOP_NAME,
        "short_name": "उधारी खाते",
        "description": "किराणा दुकानासाठी ग्राहक उधारी व्यवस्थापन",
        "lang": "mr",
        "dir": "ltr",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#faf8f2",
        "theme_color": "#0d3b2c",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "नवीन ग्राहक", "url": "/customers/new",
             "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]},
            {"name": "ग्राहक यादी", "url": "/customers",
             "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]},
        ],
    }
    resp = jsonify(data)
    resp.mimetype = "application/manifest+json"
    return resp


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(os.path.join(BASE_DIR, "static", "js"), "sw.js",
                               mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/offline")
def offline():
    return render_template("offline.html")


@app.route("/healthz")
def healthz():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ok")
    except Exception:
        return jsonify(status="db-error"), 503


# --------------------------------------------------------------------------
# Startup: tables + पहिला admin
# --------------------------------------------------------------------------
def init_db():
    db.create_all()
    # जुन्या DB साठी (टेबल आधीच होते): फोन नंबरचा unique index. नवीन DB मध्ये तो आधीच तयार झालेला असतो.
    try:
        db.session.execute(db.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_phone ON customers (phone)"))
        db.session.commit()
    except Exception as exc:  # आधीच डुप्लिकेट नंबर असतील तर
        db.session.rollback()
        print("⚠️ फोन नंबर unique index तयार झाला नाही (डुप्लिकेट नंबर आहेत?):", exc, flush=True)
    if User.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            password = secrets.token_urlsafe(9) if IS_PROD else "admin123"
            print("=" * 60, flush=True)
            print("ADMIN_PASSWORD सेट नाही. तात्पुरता लॉगिन -> %s / %s" % (username, password), flush=True)
            print("लॉगिन केल्यावर लगेच 'पासवर्ड बदला' वापरा.", flush=True)
            print("=" * 60, flush=True)
        db.session.add(User(username=username, password_hash=generate_password_hash(password)))
        db.session.commit()


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=not IS_PROD)
