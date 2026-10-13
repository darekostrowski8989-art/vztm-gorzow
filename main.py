
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for,
    session, flash, render_template_string
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get(
    "VZTM_SECRET_KEY", "zmien-ten-klucz-na-wlasny-sekret"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vztm.db")

ADMIN_USER = os.environ.get("VZTM_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get(
    "VZTM_ADMIN_PASSWORD", "VZTM-start-2026!"
)
ADMIN_HASH = generate_password_hash(ADMIN_PASSWORD)


# ============================================================
# BAZA DANYCH
# ============================================================

def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS fleet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            model TEXT NOT NULL,
            registration TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Gotowy',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Nowy',
            author TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT NOT NULL,
            date TEXT NOT NULL,
            hours TEXT NOT NULL,
            assignment TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Zaplanowany'
        );

        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Zaloguj się, aby otworzyć panel.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# ============================================================
# WSPÓLNY WYGLĄD STRONY
# ============================================================

BASE = r"""
<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#a90f2b">
<title>{{ title }} | VZTM Gorzów Wielkopolski</title>

<style>
:root {
    --red: #b51230;
    --red-dark: #7c1027;
    --ink: #182033;
    --muted: #7a8495;
    --line: #e8ebf1;
    --paper: #f4f6fa;
    --white: #ffffff;
    --green: #13845d;
    --shadow: 0 15px 45px rgba(24,32,51,.07);
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    background: var(--paper);
    color: var(--ink);
}
a { color: inherit; text-decoration: none; }
button, input, textarea, select { font: inherit; }
.topline {
    height: 5px;
    background: linear-gradient(90deg,#751026,#c51b39,#f29ba8);
}
.wrap { width: min(1160px, calc(100% - 36px)); margin: auto; }
header {
    background: rgba(255,255,255,.96);
    border-bottom: 1px solid var(--line);
    position: sticky;
    top: 0;
    z-index: 10;
}
.nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    min-height: 78px;
}
.brand {
    display: flex;
    align-items: center;
    gap: 11px;
    font-size: 20px;
    font-weight: 950;
    letter-spacing: -.7px;
}
.brand-mark {
    display: grid;
    place-items: center;
    width: 45px;
    height: 45px;
    border-radius: 14px;
    color: white;
    background: linear-gradient(145deg,#d92343,#861025);
    box-shadow: 0 7px 17px #b5123033;
}
.brand small {
    display: block;
    margin-top: 3px;
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 1.6px;
}
.navlinks {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 19px;
    font-size: 12px;
    font-weight: 750;
}
.navlinks a:hover { color: var(--red); }
.btn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    gap: 7px;
    border: 0;
    border-radius: 10px;
    background: var(--red);
    color: white;
    padding: 12px 17px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 850;
    transition: .2s;
}
.btn:hover { background: var(--red-dark); transform: translateY(-1px); }
.btn.light { background: white; color: var(--ink); border: 1px solid var(--line); }
.btn.small { padding: 8px 11px; }
.hero {
    overflow: hidden;
    color: white;
    background:
        radial-gradient(ellipse at 82% 20%,#ff748644,transparent 34%),
        linear-gradient(120deg,#191b2b,#521b30 55%,#a8112c);
}
.hero-inner {
    display: grid;
    grid-template-columns: 1.15fr .85fr;
    align-items: center;
    gap: 25px;
    min-height: 500px;
    padding-top: 55px;
    padding-bottom: 55px;
}
.eyebrow {
    color: #ffcbd3;
    text-transform: uppercase;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 2px;
}
.hero h1 {
    font-size: clamp(40px,5.3vw,67px);
    line-height: 1.02;
    letter-spacing: -2.8px;
    margin: 23px 0;
}
.hero h1 span { color: #ff9dac; }
.hero p { max-width: 510px; color: #f0dfe4; line-height: 1.9; font-size: 14px; }
.actions { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 25px; }
.hero .btn.light { background: #ffffff12; border-color: #ffffff44; color: white; }
.bus-art { position: relative; height: 280px; display: grid; place-items: center; }
.bus {
    width: min(100%,390px);
    height: 155px;
    border-radius: 23px 29px 13px 13px;
    background: linear-gradient(#fff 0 70%,#e4e7ed 70%);
    border-bottom: 10px solid #bd1735;
    position: relative;
    transform: rotate(-3deg);
    box-shadow: 0 30px 45px #100b1b66;
}
.bus:before {
    content: "";
    position: absolute;
    left: 18px; right: 18px; top: 17px;
    height: 58px;
    border: 5px solid #dfe4ea;
    border-radius: 11px 17px 4px 4px;
    background: repeating-linear-gradient(90deg,#243449 0 58px,#657083 60px 64px);
}
.bus:after {
    content: "VZTM • GORZÓW";
    position: absolute;
    left: 24px; top: 91px;
    color: #a90f2b;
    font-size: 15px;
    font-weight: 950;
    letter-spacing: 1px;
}
.wheel {
    position: absolute;
    width: 45px; height: 45px;
    left: 45px; bottom: -17px;
    border: 9px solid #202838;
    border-radius: 50%;
    background: #aeb6c2;
    box-shadow: 210px 0 0 -9px #aeb6c2,210px 0 0 0 #202838;
}
.section { padding: 65px 0; }
.section-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 25px;
}
.kicker {
    font-size: 10px;
    color: var(--red);
    font-weight: 950;
    letter-spacing: 2px;
    text-transform: uppercase;
}
h2 { letter-spacing: -1px; }
.section h2 { font-size: 34px; margin: 8px 0 0; }
.muted { color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 17px; }
.card {
    background: white;
    border: 1px solid var(--line);
    border-radius: 17px;
    padding: 23px;
    box-shadow: 0 5px 20px #18203305;
}
.card h3 { font-size: 16px; margin: 0 0 10px; }
.card p { font-size: 12px; line-height: 1.8; color: var(--muted); }
.icon {
    width: 45px; height: 45px;
    display: grid; place-items: center;
    background: #fff0f3; color: var(--red);
    border-radius: 13px;
    margin-bottom: 17px;
    font-size: 21px;
}
.tag {
    display: inline-block;
    background: #fff0f3;
    color: var(--red);
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 9px;
    font-weight: 900;
    text-transform: uppercase;
}
.cta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    padding: 30px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 19px;
}
.cta h2 { margin: 0 0 8px; }
.cta p { color: var(--muted); font-size: 12px; }
footer { background: #171b29; color: white; padding: 32px 0; margin-top: 30px; }
.foot { display: flex; justify-content: space-between; gap: 20px; align-items: center; }
.foot p { color: #b5bdca; font-size: 11px; line-height: 1.7; }
.page-head { background: white; border-bottom: 1px solid var(--line); padding: 31px 0; }
.crumb { font-size: 10px; color: var(--muted); margin-bottom: 10px; }
.page-head h1 { font-size: 32px; letter-spacing: -1px; margin: 0 0 8px; }
.page-head p { color: var(--muted); font-size: 12px; margin: 0; }
.content { padding: 28px 0 60px; }
.stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 18px; }
.stat, .panel {
    background: white;
    border: 1px solid var(--line);
    border-radius: 16px;
}
.stat { padding: 19px; }
.stat-label { color: var(--muted); font-size: 11px; }
.stat-number { font-size: 30px; font-weight: 950; margin-top: 10px; }
.two { display: grid; grid-template-columns: 1.15fr .85fr; gap: 17px; }
.panel { overflow: hidden; }
.panel-head {
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; padding: 18px 20px; border-bottom: 1px solid var(--line);
}
.panel-head h2 { font-size: 14px; margin: 0; }
.panel-body { padding: 20px; }
.shortcuts { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.shortcut { border: 1px solid var(--line); border-radius: 11px; padding: 14px; font-size: 12px; font-weight: 850; }
.shortcut:hover { border-color: #d99aa5; background: #fff9fa; }
.shortcut small { display: block; color: var(--muted); font-weight: 500; margin-top: 5px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th, td { padding: 13px 15px; text-align: left; border-bottom: 1px solid #edf0f4; white-space: nowrap; }
th { font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; background: #fafbfc; }
.pill { display: inline-block; background: #e8f7ef; color: #13764f; padding: 5px 8px; border-radius: 20px; font-size: 9px; font-weight: 900; }
.pill.warn { background: #fff3dc; color: #996000; }
.pill.red { background: #fff0f3; color: #a90f2b; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }
.field { display: flex; flex-direction: column; gap: 7px; }
.field.full { grid-column: 1 / -1; }
.field label { font-size: 10px; font-weight: 900; color: #505b6e; }
.field input, .field select, .field textarea {
    width: 100%; border: 1px solid #dce1e8; border-radius: 9px;
    padding: 11px 12px; background: white; color: var(--ink); outline: none;
}
.field input:focus, .field select:focus, .field textarea:focus {
    border-color: #c75167; box-shadow: 0 0 0 3px #b5123010;
}
.field textarea { min-height: 90px; resize: vertical; }
.alert { margin: 15px auto 0; padding: 12px 15px; border-radius: 9px; background: #fff3dc; color: #895b00; font-size: 12px; }
.alert.success { background: #e8f7ef; color: #13764f; }
.alert.error { background: #fff0f3; color: #a90f2b; }
.empty { padding: 28px 15px; text-align: center; color: var(--muted); font-size: 12px; }
.login-page { min-height: 650px; display: grid; grid-template-columns: 1fr 1fr; background: white; }
.login-visual {
    padding: 45px; color: white; display: flex; flex-direction: column;
    justify-content: space-between;
    background: radial-gradient(ellipse at 80% 15%,#ff748644,transparent 35%),linear-gradient(140deg,#1b1c2b,#76152b 65%,#b51230);
}
.login-visual h1 { font-size: clamp(35px,4vw,52px); line-height: 1.05; letter-spacing: -2px; }
.login-visual p { color: #f0dfe4; font-size: 13px; line-height: 1.8; }
.login-form-area { display: grid; place-items: center; padding: 35px; }
.login-form { width: min(390px,100%); }
.login-form h2 { font-size: 29px; margin: 10px 0; }
.login-form > p { font-size: 12px; color: var(--muted); margin-bottom: 24px; }
.login-form .field { margin-bottom: 15px; }
.login-note { margin-top: 20px; font-size: 10px; line-height: 1.7; color: var(--muted); }
@media(max-width:850px) {
    .navlinks { gap: 10px; }
    .navlinks a:not(.btn) { display: none; }
    .hero-inner { grid-template-columns: 1fr; }
    .bus-art { height: 190px; }
    .grid { grid-template-columns: 1fr 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .two { grid-template-columns: 1fr; }
    .login-page { grid-template-columns: 1fr; }
    .login-visual { display: none; }
}
@media(max-width:560px) {
    .wrap { width: calc(100% - 26px); }
    .nav { min-height: 68px; }
    .brand { font-size: 17px; }
    .brand small { font-size: 8px; }
    .hero-inner { padding: 40px 0; }
    .hero h1 { font-size: 43px; }
    .grid { grid-template-columns: 1fr; }
    .section { padding: 43px 0; }
    .section-head { align-items: start; flex-direction: column; }
    .section h2 { font-size: 28px; }
    .cta, .foot { align-items: start; flex-direction: column; }
    .stats { gap: 9px; }
    .stat { padding: 13px; }
    .stat-number { font-size: 25px; }
    .shortcuts, .form-grid { grid-template-columns: 1fr; }
    .field.full { grid-column: auto; }
    .page-head h1 { font-size: 27px; }
    .login-form-area { padding: 26px 18px; }
}
</style>
</head>
<body>
<div class="topline"></div>

<header>
<div class="wrap nav">
<a class="brand" href="{{ url_for('home') }}">
<span class="brand-mark">VZ</span>
<span>VZTM<small>GORZÓW WIELKOPOLSKI</small></span>
</a>
<nav class="navlinks">
<a href="{{ url_for('home') }}">Strona główna</a>
<a href="{{ url_for('home') }}#aktualnosci">Aktualności</a>
<a href="{{ url_for('home') }}#o-nas">O projekcie</a>
<a href="{{ url_for('rekrutacja') }}" style="background:#a90f2b;color:white;padding:9px 15px;border-radius:7px;font-weight:700">REKRUTACJA ↗</a>
{% if session.get('logged_in') %}
<a href="{{ url_for('dashboard') }}">Panel</a>
<a class="btn" href="{{ url_for('logout') }}">Wyloguj</a>
{% else %}
<a class="btn" href="{{ url_for('login') }}">Logowanie ↗</a>
{% endif %}
</nav>
</div>
</header>

{% with messages = get_flashed_messages(with_categories=true) %}
{% for category, message in messages %}
<div class="wrap"><div class="alert {{ category }}">{{ message }}</div></div>
{% endfor %}
{% endwith %}

{{ body|safe }}

<footer>
<div class="wrap foot">
<div>
<a class="brand" href="{{ url_for('home') }}" style="color:white">
<span class="brand-mark">VZ</span>
<span>VZTM<small style="color:#bdc3cf">GORZÓW WIELKOPOLSKI</small></span>
</a>
<p>Nowoczesność. Zaangażowanie. Wspólny kierunek.</p>
</div>
<p>© {{ year }} VZTM Gorzów Wielkopolski<br>Strona projektu</p>
</div>
</footer>
</body>
</html>
"""


def page(title, body, **context):
    rendered_body = render_template_string(body, **context)
    return render_template_string(
        BASE,
        title=title,
        body=rendered_body,
        year=datetime.now().year
    )


# ============================================================
# STRONA GŁÓWNA
# ============================================================

@app.route("/")
def home():
    with connect_db() as db:
        news = db.execute(
            "SELECT * FROM news ORDER BY id DESC LIMIT 3"
        ).fetchall()

    body = r"""
<section class="hero">
<div class="wrap hero-inner">
<div>
<div class="eyebrow">● &nbsp; Transport • Gorzów Wielkopolski</div>
<h1>Łączymy miasto.<br><span>Tworzymy drogę.</span></h1>
<p>Witamy na stronie VZTM Gorzów Wielkopolski.
Poznaj nasz projekt, zobacz bazę taborową i sprawdź najnowsze informacje.</p>
<div class="actions">
<a class="btn light" href="#aktualnosci">Poznaj aktualności ↓</a>
<a class="btn" href="{{ url_for('login') }}" style="background:white;color:#9d142d">Strefa pracownicza ↗</a>
</div>
</div>
<div class="bus-art"><div class="bus"><span class="wheel"></span></div></div>
</div>
</section>

<section class="section" id="o-nas">
<div class="wrap">
<div class="section-head">
<div><div class="kicker">Poznaj nas</div><h2>Jedna przestrzeń. Wiele możliwości.</h2></div>
<p class="muted" style="max-width:350px;font-size:12px;line-height:1.8">
Portal VZTM gromadzi najważniejsze informacje o projekcie i narzędzia dla zespołu.
</p>
</div>
<div class="grid">
<article class="card"><div class="icon">▤</div><h3>Tabor autobusowy</h3>
<p>Uporządkowana ewidencja pojazdów, modeli, numerów taborowych i statusów.</p></article>
<article class="card"><div class="icon">◷</div><h3>Grafiki i przydziały</h3>
<p>Planowanie zmian, zadań i przydziałów dla osób zaangażowanych w projekt.</p></article>
<article class="card"><div class="icon">▥</div><h3>Raporty i zgłoszenia</h3>
<p>Rejestr zgłoszeń i informacji, do których można wrócić w panelu.</p></article>
</div>
</div>
</section>

<section class="section" id="aktualnosci" style="padding-top:0">
<div class="wrap">
<div class="section-head"><div><div class="kicker">Co nowego?</div><h2>Aktualności</h2></div></div>
<div class="grid">
{% if news %}
{% for n in news %}
<article class="card"><span class="tag">{{ n['category'] }}</span>
<p>{{ n['created_at'] }}</p><h3>{{ n['title'] }}</h3>
<p>{{ n['content'] }}</p></article>
{% endfor %}
{% else %}
<article class="card"><span class="tag">Portal</span><h3>Witamy w VZTM</h3>
<p>To początek naszej strony. Kolejne komunikaty możesz dodawać z poziomu panelu pracownika.</p></article>
<article class="card"><span class="tag">Tabor</span><h3>Baza pojazdów</h3>
<p>Moduł taborowy pozwala prowadzić własną listę pojazdów projektu.</p></article>
<article class="card"><span class="tag">Zespół</span><h3>Strefa pracownicza</h3>
<p>Zaloguj się, aby otworzyć grafik, raporty oraz narzędzia zarządzania.</p></article>
{% endif %}
</div>
</div>
</section>

<section class="section" style="padding-top:0">
<div class="wrap cta">
<div><h2>Strefa pracownicza VZTM</h2>
<p>Zaloguj się, aby zarządzać grafikami, taborem, raportami i aktualnościami.</p></div>
<a class="btn" href="{{ url_for('login') }}">Otwórz panel ↗</a>
</div>
</section>
"""
    return page("Strona główna", body, news=news)


# ============================================================
# LOGOWANIE I WYLOGOWANIE
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USER and check_password_hash(ADMIN_HASH, password):
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            flash("Zalogowano pomyślnie.", "success")
            return redirect(url_for("dashboard"))

        flash("Nieprawidłowy login lub hasło.", "error")

    body = r"""
<div class="login-page">
<section class="login-visual">
<a class="brand" href="{{ url_for('home') }}" style="color:white">
<span class="brand-mark" style="background:white;color:#a90f2b">VZ</span>
<span>VZTM<small style="color:#f2cbd2">GORZÓW WIELKOPOLSKI</small></span>
</a>
<div>
<div class="eyebrow">STREFA PRACOWNICZA</div>
<h1>Wszystko pod kontrolą.<br><span style="color:#ff9dac">Jeden panel.</span></h1>
<p>Centrum zarządzania taborem, grafikami, raportami i aktualnościami projektu.</p>
</div>
<div style="font-size:10px;color:#e7c4cb">Panel wewnętrzny VZTM</div>
</section>

<section class="login-form-area">
<form class="login-form" method="post">
<div class="kicker">Witaj ponownie</div>
<h2>Zaloguj się</h2>
<p>Wpisz dane, aby przejść do strefy pracowniczej.</p>
<div class="field"><label for="username">LOGIN</label>
<input id="username" name="username" autocomplete="username" placeholder="Wpisz login" required autofocus></div>
<div class="field"><label for="password">HASŁO</label>
<input id="password" name="password" type="password" autocomplete="current-password" placeholder="Wpisz hasło" required></div>
<button class="btn" style="width:100%;padding:14px" type="submit">Zaloguj się →</button>
<div class="login-note">Dostęp jest przeznaczony dla uprawnionych członków zespołu.<br><br>
<a href="{{ url_for('home') }}" style="color:var(--red);font-weight:850">← Wróć na stronę główną</a></div>
</form>
</section>
</div>
"""
    return page("Logowanie", body)


@app.route("/logout")
def logout():
    session.clear()
    flash("Wylogowano z panelu.", "success")
    return redirect(url_for("home"))


# ============================================================
# PULPIT ADMINISTRACYJNY
# ============================================================

@app.route("/panel")
@login_required
def dashboard():
    with connect_db() as db:
        vehicles = db.execute("SELECT COUNT(*) FROM fleet").fetchone()[0]
        ready = db.execute(
            "SELECT COUNT(*) FROM fleet WHERE status='Gotowy'"
        ).fetchone()[0]
        reports = db.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        open_reports = db.execute(
            "SELECT COUNT(*) FROM reports WHERE status!='Zamknięty'"
        ).fetchone()[0]
        shifts = db.execute("SELECT COUNT(*) FROM shifts").fetchone()[0]
        news_count = db.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        recent = db.execute(
            "SELECT * FROM reports ORDER BY id DESC LIMIT 5"
        ).fetchall()

    body = r"""
<div class="page-head"><div class="wrap">
<div class="crumb">VZTM / Panel główny</div>
<h1>Centrum zarządzania</h1>
<p>Witaj, {{ session.get('username') }}. Oto podsumowanie projektu.</p>
</div></div>

<div class="content"><div class="wrap">
<div class="box" style="margin-bottom:18px"><h2>Rekrutacja</h2><p>Sprawdzaj zgłoszenia oraz wyniki kandydatów.</p><a class="btn" href="/panel/wyniki-rekrutacji">Wyniki rekrutacji</a></div>
<div class="stats">
<div class="stat"><div class="stat-label">Pojazdy w bazie</div><div class="stat-number">{{ vehicles }}</div><span class="muted">Cały tabor</span></div>
<div class="stat"><div class="stat-label">Pojazdy gotowe</div><div class="stat-number">{{ ready }}</div><span class="muted">Status: Gotowy</span></div>
<div class="stat"><div class="stat-label">Raporty otwarte</div><div class="stat-number">{{ open_reports }}</div><span class="muted">Do obsłużenia</span></div>
<div class="stat"><div class="stat-label">Zaplanowane zmiany</div><div class="stat-number">{{ shifts }}</div><span class="muted">Wpisy w grafiku</span></div>
</div>

<div class="two">
<section class="panel">
<div class="panel-head"><h2>Moduły systemu</h2><span class="pill">PANEL VZTM</span></div>
<div class="panel-body"><div class="shortcuts">
<a class="shortcut" href="{{ url_for('fleet') }}">▤ &nbsp; Tabor autobusowy<small>{{ vehicles }} pojazdów w bazie</small></a>
<a class="shortcut" href="{{ url_for('schedule') }}">◷ &nbsp; Grafik pracy<small>{{ shifts }} zapisanych zmian</small></a>
<a class="shortcut" href="{{ url_for('reports') }}">▥ &nbsp; Raporty<small>{{ reports }} wszystkich raportów</small></a>
<a class="shortcut" href="{{ url_for('news_admin') }}">✦ &nbsp; Aktualności<small>{{ news_count }} komunikatów</small></a>
</div></div>
</section>

<section class="panel">
<div class="panel-head"><h2>Ostatnie raporty</h2><a href="{{ url_for('reports') }}" style="font-size:10px;color:var(--red)">Wszystkie →</a></div>
{% if recent %}
<div class="table-wrap"><table><thead><tr><th>Zgłoszenie</th><th>Status</th></tr></thead><tbody>
{% for r in recent %}
<tr><td><b>{{ r['title'] }}</b><br><span class="muted">{{ r['category'] }}</span></td>
<td><span class="pill {{ 'red' if r['status']=='Nowy' else ('warn' if r['status']!='Zamknięty' else '') }}">{{ r['status'] }}</span></td></tr>
{% endfor %}
</tbody></table></div>
{% else %}<div class="empty">Brak raportów. Możesz utworzyć pierwszy.</div>{% endif %}
</section>
</div>
</div></div>
"""
    return page(
        "Panel zarządzania", body,
        vehicles=vehicles, ready=ready, reports=reports,
        open_reports=open_reports, shifts=shifts,
        news_count=news_count, recent=recent
    )


# ============================================================
# TABOR
# ============================================================

@app.route("/tabor", methods=["GET", "POST"])
@login_required
def fleet():
    if request.method == "POST":
        number = request.form.get("number", "").strip()
        model = request.form.get("model", "").strip()
        if not number or not model:
            flash("Numer taborowy i model są wymagane.", "error")
        else:
            with connect_db() as db:
                db.execute("""
                    INSERT INTO fleet
                    (number,model,registration,status,notes,created_at)
                    VALUES (?,?,?,?,?,?)
                """, (
                    number, model,
                    request.form.get("registration", "").strip(),
                    request.form.get("status", "Gotowy"),
                    request.form.get("notes", "").strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ))
            flash("Dodano pojazd do bazy taborowej.", "success")
            return redirect(url_for("fleet"))

    with connect_db() as db:
        vehicles = db.execute("SELECT * FROM fleet ORDER BY number").fetchall()

    body = r"""
<div class="page-head"><div class="wrap"><div class="crumb">Panel / Tabor</div>
<h1>Tabor autobusowy</h1><p>Rejestr pojazdów, numerów taborowych i statusów.</p></div></div>
<div class="content"><div class="wrap"><div class="two">
<section class="panel"><div class="panel-head"><h2>Lista pojazdów</h2><span class="pill">{{ vehicles|length }} pojazdów</span></div>
{% if vehicles %}
<div class="table-wrap"><table><thead><tr><th>Numer</th><th>Model</th><th>Rejestracja</th><th>Status</th></tr></thead><tbody>
{% for v in vehicles %}<tr><td><b>{{ v['number'] }}</b></td><td>{{ v['model'] }}</td><td>{{ v['registration'] or '—' }}</td>
<td><span class="pill {{ 'red' if v['status']=='Serwis' else ('warn' if v['status']=='Rezerwa' else '') }}">{{ v['status'] }}</span></td></tr>{% endfor %}
</tbody></table></div>
{% else %}<div class="empty">Baza jest pusta. Dodaj pierwszy pojazd w formularzu.</div>{% endif %}
</section>

<section class="panel"><div class="panel-head"><h2>Dodaj pojazd</h2></div><div class="panel-body">
<form method="post" class="form-grid">
<div class="field"><label>NUMER TABOROWY *</label><input name="number" placeholder="np. 101" required></div>
<div class="field"><label>MODEL *</label><input name="model" placeholder="np. Solaris Urbino 12" required></div>
<div class="field"><label>REJESTRACJA</label><input name="registration" placeholder="np. FG 12345"></div>
<div class="field"><label>STATUS</label><select name="status"><option>Gotowy</option><option>Rezerwa</option><option>Serwis</option><option>Wycofany</option></select></div>
<div class="field full"><label>NOTATKI</label><textarea name="notes" placeholder="Dodatkowe informacje"></textarea></div>
<div class="field full"><button class="btn">＋ Dodaj pojazd</button></div>
</form></div></section>
</div></div></div>
"""
    return page("Tabor autobusowy", body, vehicles=vehicles)


# ============================================================
# GRAFIK
# ============================================================

@app.route("/grafik", methods=["GET", "POST"])
@login_required
def schedule():
    if request.method == "POST":
        employee = request.form.get("employee", "").strip()
        date = request.form.get("date", "").strip()
        hours = request.form.get("hours", "").strip()
        if not employee or not date or not hours:
            flash("Uzupełnij pracownika, datę i godziny.", "error")
        else:
            with connect_db() as db:
                db.execute("""
                    INSERT INTO shifts (employee,date,hours,assignment,status)
                    VALUES (?,?,?,?,?)
                """, (
                    employee, date, hours,
                    request.form.get("assignment", "").strip(),
                    request.form.get("status", "Zaplanowany")
                ))
            flash("Dodano zmianę do grafiku.", "success")
            return redirect(url_for("schedule"))

    with connect_db() as db:
        shifts = db.execute(
            "SELECT * FROM shifts ORDER BY date DESC, id DESC"
        ).fetchall()

    body = r"""
<div class="page-head"><div class="wrap"><div class="crumb">Panel / Grafik</div>
<h1>Grafik i przydziały</h1><p>Planowanie zmian i zadań zespołu.</p></div></div>
<div class="content"><div class="wrap"><div class="two">
<section class="panel"><div class="panel-head"><h2>Zaplanowane zmiany</h2><span class="pill">{{ shifts|length }} wpisów</span></div>
{% if shifts %}<div class="table-wrap"><table><thead><tr><th>Osoba</th><th>Data</th><th>Godziny</th><th>Przydział</th><th>Status</th></tr></thead><tbody>
{% for s in shifts %}<tr><td><b>{{ s['employee'] }}</b></td><td>{{ s['date'] }}</td><td>{{ s['hours'] }}</td><td>{{ s['assignment'] or '—' }}</td>
<td><span class="pill {{ 'warn' if s['status']=='Do potwierdzenia' else '' }}">{{ s['status'] }}</span></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">Nie ma jeszcze wpisów w grafiku.</div>{% endif %}
</section>
<section class="panel"><div class="panel-head"><h2>Dodaj zmianę</h2></div><div class="panel-body">
<form method="post" class="form-grid">
<div class="field full"><label>PRACOWNIK *</label><input name="employee" placeholder="Imię i nazwisko / nick" required></div>
<div class="field"><label>DATA *</label><input type="date" name="date" required></div>
<div class="field"><label>GODZINY *</label><input name="hours" placeholder="06:00–14:00" required></div>
<div class="field full"><label>PRZYDZIAŁ</label><input name="assignment" placeholder="np. linia, pojazd lub zadanie"></div>
<div class="field full"><label>STATUS</label><select name="status"><option>Zaplanowany</option><option>Do potwierdzenia</option><option>Zrealizowany</option></select></div>
<div class="field full"><button class="btn">＋ Dodaj zmianę</button></div>
</form></div></section>
</div></div></div>
"""
    return page("Grafik pracy", body, shifts=shifts)


# ============================================================
# RAPORTY
# ============================================================

@app.route("/raporty", methods=["GET", "POST"])
@login_required
def reports():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Inne").strip()
        description = request.form.get("description", "").strip()
        if not title:
            flash("Podaj tytuł raportu.", "error")
        else:
            with connect_db() as db:
                db.execute("""
                    INSERT INTO reports
                    (title,category,description,status,author,created_at)
                    VALUES (?,?,?,?,?,?)
                """, (
                    title, category, description, "Nowy",
                    session.get("username", "admin"),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ))
            flash("Raport został zapisany.", "success")
            return redirect(url_for("reports"))

    with connect_db() as db:
        items = db.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

    body = r"""
<div class="page-head"><div class="wrap"><div class="crumb">Panel / Raporty</div>
<h1>Raporty i zgłoszenia</h1><p>Rejestr spraw organizacyjnych, usterek i informacji.</p></div></div>
<div class="content"><div class="wrap"><div class="two">
<section class="panel"><div class="panel-head"><h2>Rejestr raportów</h2><span class="pill">{{ items|length }} wpisów</span></div>
{% if items %}<div class="table-wrap"><table><thead><tr><th>ID</th><th>Tytuł / opis</th><th>Kategoria</th><th>Autor</th><th>Data</th><th>Status</th></tr></thead><tbody>
{% for r in items %}<tr><td>#{{ r['id'] }}</td><td><b>{{ r['title'] }}</b><br><span class="muted">{{ r['description'][:70] }}</span></td><td>{{ r['category'] }}</td><td>{{ r['author'] }}</td><td>{{ r['created_at'] }}</td><td><span class="pill {{ 'red' if r['status']=='Nowy' else ('warn' if r['status']!='Zamknięty' else '') }}">{{ r['status'] }}</span></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">Nie ma jeszcze raportów.</div>{% endif %}
</section>
<section class="panel"><div class="panel-head"><h2>Nowy raport</h2></div><div class="panel-body">
<form method="post" class="form-grid">
<div class="field full"><label>TYTUŁ *</label><input name="title" placeholder="Krótki opis sprawy" required></div>
<div class="field full"><label>KATEGORIA</label><select name="category"><option>Tabor</option><option>Grafik</option><option>Organizacja</option><option>Usterka</option><option>Inne</option></select></div>
<div class="field full"><label>OPIS</label><textarea name="description" placeholder="Opisz sytuację i ważne szczegóły"></textarea></div>
<div class="field full"><button class="btn">＋ Zapisz raport</button></div>
</form></div></section>
</div></div></div>
"""
    return page("Raporty", body, items=items)


# ============================================================
# AKTUALNOŚCI — DODAWANIE DO STRONY GŁÓWNEJ
# ============================================================

@app.route("/aktualnosci", methods=["GET", "POST"])
@login_required
def news_admin():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Informacja").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Tytuł i treść są wymagane.", "error")
        else:
            with connect_db() as db:
                db.execute("""
                    INSERT INTO news (title,category,content,created_at)
                    VALUES (?,?,?,?)
                """, (
                    title, category, content,
                    datetime.now().strftime("%Y-%m-%d")
                ))
            flash("Aktualność została opublikowana.", "success")
            return redirect(url_for("news_admin"))

    with connect_db() as db:
        items = db.execute("SELECT * FROM news ORDER BY id DESC").fetchall()

    body = r"""
<div class="page-head"><div class="wrap"><div class="crumb">Panel / Aktualności</div>
<h1>Aktualności</h1><p>Publikuj komunikaty wyświetlane na stronie głównej.</p></div></div>
<div class="content"><div class="wrap"><div class="two">
<section class="panel"><div class="panel-head"><h2>Opublikowane wpisy</h2><span class="pill">{{ items|length }}</span></div>
{% if items %}<div class="panel-body">{% for n in items %}
<div style="padding:12px 0;border-bottom:1px solid var(--line)">
<span class="tag">{{ n['category'] }}</span><h3>{{ n['title'] }}</h3>
<p class="muted" style="font-size:11px">{{ n['created_at'] }}</p><p style="font-size:12px;line-height:1.7">{{ n['content'] }}</p>
</div>{% endfor %}</div>{% else %}<div class="empty">Brak opublikowanych aktualności.</div>{% endif %}
</section>
<section class="panel"><div class="panel-head"><h2>Opublikuj aktualność</h2></div><div class="panel-body">
<form method="post" class="form-grid">
<div class="field full"><label>TYTUŁ *</label><input name="title" required placeholder="Tytuł komunikatu"></div>
<div class="field full"><label>KATEGORIA</label><select name="category"><option>Informacja</option><option>Tabor</option><option>Organizacja</option><option>Ważne</option></select></div>
<div class="field full"><label>TREŚĆ *</label><textarea name="content" required placeholder="Treść aktualności"></textarea></div>
<div class="field full"><button class="btn">Opublikuj →</button></div>
</form></div></section>
</div></div></div>
"""
    return page("Aktualności", body, items=items)


# ============================================================
# START APLIKACJI
# ============================================================

init_db()


# ===== REKRUTACJA VZTM =====
import json as _rekrutacja_json
from datetime import datetime as _rekrutacja_datetime

_REKRUTACJA_DB = os.path.join(BASE_DIR, "rekrutacja.db")
_REKRUTACJA_PYTANIA = [
("Dane kandydata", [
("imie", "Imię i nazwisko", "text"),
("wiek", "Wiek", "number"),
("discord", "Nazwa użytkownika Discord", "text"),
("kontakt", "Dodatkowy kontakt", "text"),
("strefa", "Strefa czasowa / kraj", "text")]),
("Doświadczenie", [
("doswiadczenie", "Czy masz doświadczenie w wirtualnej komunikacji?", "select"),
("gry", "W jakich grach symulacyjnych grasz?", "text"),
("firmy", "Czy pracowałeś w innych wirtualnych firmach?", "text"),
("stanowisko", "Jakie stanowiska wcześniej pełniłeś?", "text"),
("powod", "Dlaczego odszedłeś z poprzednich firm?", "text")]),
("Dyspozycyjność", [
("dni", "W jakie dni możesz jeździć?", "text"),
("godziny", "W jakich godzinach jesteś dostępny?", "text"),
("czas", "Ile godzin tygodniowo możesz poświęcić?", "text"),
("nieobecnosci", "Czy planujesz dłuższe nieobecności?", "text"),
("aktywnosc", "Jak oceniasz swoją aktywność 1–10?", "number")]),
("Wiedza i umiejętności", [
("przepisy", "Jak ważne jest przestrzeganie regulaminu?", "text"),
("pasazer", "Jak zachowasz się wobec trudnego pasażera?", "text"),
("spoznienie", "Co zrobisz, gdy spóźnisz się na zmianę?", "text"),
("usterka", "Co zrobisz w razie awarii pojazdu?", "text"),
("trasa", "Czy potrafisz korzystać z rozkładu jazdy?", "select")]),
("Motywacja", [
("motywacja", "Dlaczego chcesz dołączyć do VZTM Gorzów Wielkopolski?", "textarea"),
("zalety", "Jakie są Twoje największe zalety?", "textarea"),
("wady", "Nad czym chcesz jeszcze popracować?", "textarea"),
("zespol", "Jak współpracujesz z innymi?", "textarea"),
("cele", "Jakie masz cele w naszej firmie?", "textarea")]),
("Ostatnie pytania", [
("pojazd", "Jakim autobusem chciałbyś jeździć?", "text"),
("linie", "Jakie linie chciałbyś obsługiwać?", "text"),
("sprzet", "Czy masz sprawny sprzęt i stabilne połączenie?", "select"),
("regulamin", "Czy zobowiązujesz się przestrzegać regulaminu?", "select"),
("uwagi", "Dodatkowe informacje dla rekrutera", "textarea")])
]

def _rekrutacja_polacz():
    db = sqlite3.connect(_REKRUTACJA_DB)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        discord TEXT NOT NULL,
        answers TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Nowe',
        created_at TEXT NOT NULL
    )""")
    db.commit()
    return db

def _rekrutacja_strona(tytul, tresc):
    return render_template_string("""
    <!doctype html><html lang="pl"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ tytul }} — VZTM Gorzów Wielkopolski</title>
    <style>
    body{margin:0;background:#10131a;color:#f5f5f5;font:16px Arial}
    header{background:#a90f2b;padding:22px;text-align:center}
    main{max-width:850px;margin:30px auto;padding:20px}
    .box{background:#1c222d;padding:22px;border-radius:12px;margin:15px 0}
    label{display:block;margin:15px 0 7px}
    input,textarea,select{box-sizing:border-box;width:100%;padding:12px;border-radius:7px;border:1px solid #555;background:#111722;color:white}
    textarea{min-height:90px}button,.btn{display:inline-block;background:#bd1836;color:white;border:0;border-radius:7px;padding:12px 18px;cursor:pointer;text-decoration:none;margin:8px 5px 8px 0}
    .muted{color:#c1c7d0}.stage{display:none}.stage.active{display:block}
    progress{width:100%;height:18px;accent-color:#bd1836}
    a{color:#ff8da2}
    </style>
    <header><h1>VZTM GORZÓW WIELKOPOLSKI</h1><p>Rekrutacja kierowców</p></header>
    <main>{{ tresc|safe }}</main></html>
    """, tytul=tytul, tresc=tresc)

@app.route("/rekrutacja", methods=["GET", "POST"])
def rekrutacja():
    if request.method == "POST":
        odpowiedzi = {}
        for nazwa, pytania in _REKRUTACJA_PYTANIA:
            for klucz, pytanie, typ in pytania:
                wartosc = request.form.get(klucz, "").strip()
                if klucz != "uwagi" and not wartosc:
                    return _rekrutacja_strona("Uzupełnij formularz",
                        "<div class='box'><h2>Nie wszystkie pola zostały wypełnione.</h2><a class='btn' href='/rekrutacja'>Wróć do formularza</a></div>"), 400
                odpowiedzi[pytanie] = wartosc
        imie = request.form.get("imie", "").strip()
        discord = request.form.get("discord", "").strip()
        if len(imie) < 3 or len(discord) < 2:
            return _rekrutacja_strona("Błędne dane",
                "<div class='box'>Podaj poprawne imię i nazwisko oraz nazwę Discord.</div>"), 400
        db = _rekrutacja_polacz()
        db.execute("INSERT INTO applications(name,discord,answers,status,created_at) VALUES(?,?,?,?,?)",
            (imie, discord, _rekrutacja_json.dumps(odpowiedzi, ensure_ascii=False),
             "Nowe", _rekrutacja_datetime.now().strftime("%Y-%m-%d %H:%M")))
        db.commit()
        db.close()
        return _rekrutacja_strona("Zgłoszenie wysłane",
            "<div class='box'><h2>Dziękujemy za zgłoszenie!</h2><p>Twoja aplikacja została zapisana. Zarząd VZTM rozpatrzy ją w swoim czasie.</p><a class='btn' href='/'>Strona główna</a></div>")

    pola = []
    numer = 0
    for etap, pytania in _REKRUTACJA_PYTANIA:
        pola.append("<section class='stage'><div class='box'><h2>" + etap + "</h2>")
        for klucz, pytanie, typ in pytania:
            numer += 1
            label = "<label for='" + klucz + "'>" + str(numer) + ". " + pytanie + "</label>"
            if typ == "select":
                opcje = "<option value=''>Wybierz odpowiedź</option><option>Tak</option><option>Nie</option><option>Częściowo</option>"
                pole = "<select required name='" + klucz + "' id='" + klucz + "'>" + opcje + "</select>"
            elif typ == "textarea":
                pole = "<textarea required name='" + klucz + "' id='" + klucz + "'></textarea>"
            else:
                input_type = "number" if typ == "number" else "text"
                pole = "<input required type='" + input_type + "' name='" + klucz + "' id='" + klucz + "'>"
            pola.append(label + pole)
        pola.append("</div></section>")
    pola.append("<div class='box'><label><input style='width:auto' type='checkbox' required> Potwierdzam, że podane informacje są prawdziwe.</label><button type='submit'>Wyślij zgłoszenie</button></div>")
    tresc = "<div class='box'><p>Wypełnij 30 pytań w sześciu etapach.</p><progress id='postep' max='6' value='1'></progress><p id='licznik'></p></div><form method='post' id='formularz'>" + "".join(pola) + "<div class='box'><button type='button' id='wstecz'>Wstecz</button><button type='button' id='dalej'>Dalej</button></div></form><script>let n=0,s=[...document.querySelectorAll('.stage')],p=document.getElementById('postep'),l=document.getElementById('licznik');function pokaz(){s.forEach((x,i)=>x.classList.toggle('active',i===n));p.value=n+1;l.textContent='Etap '+(n+1)+' z '+s.length;document.getElementById('wstecz').style.display=n===0?'none':'inline-block';document.getElementById('dalej').style.display=n===s.length-1?'none':'inline-block'}function sprawdz(){let ok=true;s[n].querySelectorAll('input,textarea,select').forEach(x=>{if(!x.checkValidity()){x.reportValidity();ok=false}});return ok}document.getElementById('dalej').onclick=()=>{if(sprawdz()&&n<s.length-1){n++;pokaz();window.scrollTo(0,0)}};document.getElementById('wstecz').onclick=()=>{n=Math.max(0,n-1);pokaz();window.scrollTo(0,0)};document.getElementById('formularz').onsubmit=e=>{if(!sprawdz())e.preventDefault()};pokaz();</script>"
    return _rekrutacja_strona("Rekrutacja", tresc)

@app.route("/panel/rekrutacja")
@login_required
def panel_rekrutacji():
    db = _rekrutacja_polacz()
    aplikacje = db.execute("SELECT id,name,discord,status,created_at FROM applications ORDER BY id DESC").fetchall()
    db.close()
    wiersze = "".join("<tr><td>"+str(a["id"])+"</td><td>"+a["name"]+"</td><td>"+a["discord"]+"</td><td>"+a["status"]+"</td><td>"+a["created_at"]+"</td><td><a href='/panel/rekrutacja/"+str(a["id"])+"'>Otwórz</a></td></tr>" for a in aplikacje)
    tresc = "<div class='box'><h2>Zgłoszenia kandydatów</h2><table style='width:100%;text-align:left'><tr><th>ID</th><th>Kandydat</th><th>Discord</th><th>Status</th><th>Data</th><th></th></tr>"+(wiersze or "<tr><td colspan='6'>Brak zgłoszeń.</td></tr>")+"</table></div><a class='btn' href='/panel'>Wróć do panelu</a>"
    return _rekrutacja_strona("Panel rekrutacji", tresc)

@app.route("/panel/rekrutacja/<int:application_id>", methods=["GET", "POST"])
@login_required
def szczegoly_rekrutacji(application_id):
    db = _rekrutacja_polacz()
    a = db.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    if not a:
        db.close()
        return "Nie znaleziono zgłoszenia.", 404
    if request.method == "POST":
        status = request.form.get("status", "Nowe")
        if status not in ["Nowe", "W trakcie", "Przyjęty", "Odrzucony"]:
            status = "Nowe"
        db.execute("UPDATE applications SET status=? WHERE id=?", (status, application_id))
        db.commit()
        a = db.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    db.close()
    odpowiedzi = _rekrutacja_json.loads(a["answers"])
    tresc = "<div class='box'><h2>"+a["name"]+"</h2><p>Discord: "+a["discord"]+"</p><p>Data: "+a["created_at"]+"</p><form method='post'><label>Status</label><select name='status'>"
    for status in ["Nowe", "W trakcie", "Przyjęty", "Odrzucony"]:
        selected = " selected" if status == a["status"] else ""
        tresc += "<option"+selected+">"+status+"</option>"
    tresc += "</select><button>Zapisz status</button></form></div>"
    for pytanie, odpowiedz in odpowiedzi.items():
        tresc += "<div class='box'><h3>"+pytanie+"</h3><p>"+str(odpowiedz).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")+"</p></div>"
    tresc += "<a class='btn' href='/panel/rekrutacja'>Wróć do zgłoszeń</a>"
    return _rekrutacja_strona("Szczegóły zgłoszenia", tresc)


@app.route("/panel/wyniki-rekrutacji")
@login_required
def wyniki_rekrutacji():
    db = _rekrutacja_polacz()
    aplikacje = db.execute(
        "SELECT id,name,discord,status,created_at FROM applications ORDER BY id DESC"
    ).fetchall()
    db.close()

    esc = lambda value: str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    wiersze = ""
    for a in aplikacje:
        status = esc(a["status"])
        wiersze += (
            "<tr><td>" + str(a["id"]) + "</td>"
            "<td><b>" + esc(a["name"]) + "</b></td>"
            "<td>" + esc(a["discord"]) + "</td>"
            "<td><span class='tag'>" + status + "</span></td>"
            "<td>" + esc(a["created_at"]) + "</td>"
            "<td><a class='btn' href='/panel/rekrutacja/" + str(a["id"]) + "'>Zobacz wynik</a></td></tr>"
        )

    tresc = (
        "<div class='box'><h2>Wyniki rekrutacji</h2>"
        "<p>Lista zgłoszeń i aktualnych wyników kandydatów.</p>"
        "<div style='overflow-x:auto'><table style='width:100%;text-align:left;border-collapse:collapse'>"
        "<tr><th>ID</th><th>Kandydat</th><th>Discord</th><th>Wynik</th><th>Data</th><th>Szczegóły</th></tr>"
        + (wiersze or "<tr><td colspan='6'>Brak zgłoszeń rekrutacyjnych.</td></tr>")
        + "</table></div></div><a class='btn' href='/panel'>Wróć do panelu</a>"
    )
    return _rekrutacja_strona("Wyniki rekrutacji", tresc)

# ===== KONIEC REKRUTACJI =====

if __name__ == "__main__":
    # Lokalnie otwórz http://127.0.0.1:5000
    # Do publicznego hostingu użyj konfiguracji zalecanej przez dostawcę.
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=False
    )


