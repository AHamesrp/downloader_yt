import os
import pathlib
import re
import secrets
import sys
import threading
import time
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
import yt_dlp

from auth_db import (
    create_login_otp,
    create_user,
    get_user_by_email,
    get_user_by_id,
    init_db,
    verify_login_otp,
    with_connection,
)
from auth_mail import send_2fa_code

# Detecta se está rodando empacotado pelo PyInstaller
if getattr(sys, "frozen", False):
    BASE_DIR = pathlib.Path(sys.executable).resolve().parent
else:
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

FRONT_DIR = BASE_DIR / "front"
DATA_DIR = BASE_DIR / "data"
AUTH_DB_PATH = DATA_DIR / "aurorayt_auth.db"

DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")

_secret = os.environ.get("SECRET_KEY", "").strip()
if not _secret:
    if os.environ.get("PRODUCTION", "").lower() in ("1", "true", "yes"):
        raise SystemExit("Em produção é obrigatório definir a variável de ambiente SECRET_KEY.")
    _secret = "dev-only-insecure-secret-change-me"
    print(
        "AVISO: SECRET_KEY não definida — usando chave de desenvolvimento. "
        "Para produção, defina SECRET_KEY (e opcionalmente PRODUCTION=1).",
        file=sys.stderr,
    )
app = Flask(__name__)
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # JSON pequeno; evita corpos enormes
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in (
    "1",
    "true",
    "yes",
)

# CORS: credenciais (cookies) exigem origem explícita — não use * com sessão
_default_cors = "http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:5500"
_cors = os.environ.get("CORS_ORIGINS", _default_cors).strip()
_origins_list = [o.strip() for o in _cors.split(",") if o.strip()]
if _cors == "*":
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    CORS(
        app,
        resources={r"/api/*": {"origins": _origins_list, "supports_credentials": True}},
    )

init_db(AUTH_DB_PATH)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_auth_rate_lock = threading.Lock()
_auth_rate_hits: dict[str, list[float]] = {}

_progress_lock = threading.Lock()
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}

MAX_URLS_PER_REQUEST = int(os.environ.get("MAX_URLS_PER_REQUEST", "25"))
MAX_URL_LENGTH = int(os.environ.get("MAX_URL_LENGTH", "2048"))
RATE_WINDOW_SEC = int(os.environ.get("RATE_WINDOW_SEC", "60"))
RATE_MAX_DOWNLOADS = int(os.environ.get("RATE_MAX_DOWNLOADS", "8"))


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Não expor tecnologia do servidor
    response.headers.pop("Server", None)
    return response


def _client_ip() -> str:
    return (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or (request.remote_addr or "unknown")


def _rate_limit_download() -> bool:
    """True se permitido, False se excedeu limite."""
    ip = _client_ip()
    now = time.monotonic()
    with _rate_lock:
        bucket = [t for t in _rate_buckets.get(ip, []) if now - t < RATE_WINDOW_SEC]
        if len(bucket) >= RATE_MAX_DOWNLOADS:
            return False
        bucket.append(now)
        _rate_buckets[ip] = bucket
    return True


def _is_allowed_youtube_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    s = url.strip()
    if not s or len(s) > MAX_URL_LENGTH:
        return False
    if "\n" in s or "\r" in s or "\x00" in s:
        return False
    if ".." in s:
        return False
    if not s.startswith(("http://", "https://")):
        s = "https://" + s
    try:
        p = urlparse(s)
    except ValueError:
        return False
    if p.scheme != "https":
        return False
    netloc = (p.netloc or "").lower()
    if not netloc or "@" in netloc:
        return False
    host = netloc.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    path = p.path or ""
    query = p.query or ""

    if host == "youtu.be":
        return bool(re.match(r"^/[A-Za-z0-9_-]{6,}(\?.*)?$", path))

    if host == "youtube.com" or host.endswith(".youtube.com"):
        pl = path.lower()
        if re.search(r"[\s<>\"{}|\\^`\[\]]", path + "?" + query):
            return False
        if pl.startswith("/watch"):
            return "v=" in query or "list=" in query
        if pl.startswith("/shorts/"):
            return len(path) > 8
        if pl.startswith("/live/"):
            return len(path) > 6
        if pl.startswith("/embed/"):
            return len(path) > 8
        if pl.startswith("/v/"):
            return len(path) > 3
        return False

    return False


def _progress_update(**kwargs) -> None:
    with _progress_lock:
        progress_state.update(kwargs)


def _sanitize_urls(raw: list) -> tuple[list[str], str | None]:
    if not isinstance(raw, list):
        return [], "Formato inválido."
    if len(raw) == 0:
        return [], "Envie pelo menos uma URL."
    if len(raw) > MAX_URLS_PER_REQUEST:
        return [], f"No máximo {MAX_URLS_PER_REQUEST} links por vez."
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            return [], "Cada item deve ser texto (URL)."
        if not _is_allowed_youtube_url(item):
            return [], "Uma ou mais URLs não são do YouTube ou não são permitidas."
        norm = item.strip()
        if not norm.startswith(("http://", "https://")):
            norm = "https://" + norm
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    if not out:
        return [], "Nenhuma URL válida após validação."
    return out, None


def _public_error(_internal: str) -> str:
    if DEBUG:
        return _internal
    return "Não foi possível concluir a operação."


def _auth_rate_ok(bucket_key: str, max_n: int = 15, window: float = 60.0) -> bool:
    now = time.monotonic()
    with _auth_rate_lock:
        bucket = [t for t in _auth_rate_hits.get(bucket_key, []) if now - t < window]
        if len(bucket) >= max_n:
            return False
        bucket.append(now)
        _auth_rate_hits[bucket_key] = bucket
    return True


def require_login(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Não autenticado."}), 401
        return f(*args, **kwargs)

    return wrapped


# Estado simples de progresso (um "job" por vez, suficiente para uso local)
progress_state = {
    "status": "idle",          # idle | downloading | done | error
    "percent": 0,              # 0–100 (geral)
    "current_video": None,     # URL atual
    "current_video_percent": 0,
    "index": 0,                # índice do vídeo atual (1-based)
    "total": 0,                # total de vídeos
    "message": "",
}


@app.get("/")
def serve_front():
    """Serve o index.html do front como página principal."""
    return send_from_directory(FRONT_DIR, "index.html")


@app.get("/login.html")
def serve_login_page():
    return send_from_directory(FRONT_DIR, "login.html")


@app.get("/api/auth/me")
def auth_me():
    uid = session.get("user_id")
    if uid:
        email = session.get("user_email")
        if not email:

            def load_email(conn):
                u = get_user_by_id(conn, int(uid))
                return u["email"] if u else None

            email = with_connection(AUTH_DB_PATH, load_email)
            if email:
                session["user_email"] = email
        return jsonify({"authenticated": True, "email": email})
    if session.get("pending_2fa_uid"):
        return jsonify(
            {
                "authenticated": False,
                "pending2fa": True,
                "email": session.get("pending_2fa_email"),
            }
        )
    return jsonify({"authenticated": False, "pending2fa": False})


@app.post("/api/auth/register")
def auth_register():
    if not _auth_rate_ok(f"reg:{_client_ip()}"):
        return jsonify({"error": "Muitas tentativas. Aguarde um minuto."}), 429
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Dados inválidos."}), 400
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not EMAIL_RE.match(email) or len(email) > 254:
        return jsonify({"error": "E-mail inválido."}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "A senha deve ter pelo menos 8 caracteres."}), 400
    if len(password) > 256:
        return jsonify({"error": "Senha muito longa."}), 400

    ph = generate_password_hash(password)

    def ins(conn):
        return create_user(conn, email, ph)

    new_id = with_connection(AUTH_DB_PATH, ins)
    if new_id is None:
        return jsonify({"error": "Este e-mail já está cadastrado."}), 409
    return jsonify({"ok": True}), 201


@app.post("/api/auth/login")
def auth_login():
    if not _auth_rate_ok(f"login:{_client_ip()}"):
        return jsonify({"error": "Muitas tentativas. Aguarde um minuto."}), 429
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Dados inválidos."}), 400
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    def lookup(conn):
        return get_user_by_email(conn, email)

    user = with_connection(AUTH_DB_PATH, lookup)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "E-mail ou senha incorretos."}), 401

    code = f"{secrets.randbelow(1000000):06d}"
    ch = generate_password_hash(code)

    def save_otp(conn):
        create_login_otp(conn, int(user["id"]), ch)

    with_connection(AUTH_DB_PATH, save_otp)

    sent, mail_note = send_2fa_code(user["email"], code, app.logger)
    session.clear()
    session["pending_2fa_uid"] = int(user["id"])
    session["pending_2fa_email"] = user["email"]
    return jsonify(
        {
            "need2fa": True,
            "emailSent": sent,
            "emailHint": user["email"],
            "message": mail_note,
        }
    )


@app.post("/api/auth/verify-2fa")
def auth_verify_2fa():
    if not _auth_rate_ok(f"2fa:{_client_ip()}", max_n=20, window=60.0):
        return jsonify({"error": "Muitas tentativas. Aguarde um minuto."}), 429
    uid = session.get("pending_2fa_uid")
    if not uid:
        return jsonify({"error": "Não há verificação pendente. Faça login de novo."}), 400
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().replace(" ", "")
    if not re.fullmatch(r"\d{6}", code):
        return jsonify({"error": "Informe o código de 6 dígitos."}), 400

    def verify(conn):
        return verify_login_otp(conn, int(uid), code)

    if not with_connection(AUTH_DB_PATH, verify):
        return jsonify({"error": "Código incorreto ou expirado."}), 401

    email = session.pop("pending_2fa_email", None)
    session.pop("pending_2fa_uid", None)
    session["user_id"] = int(uid)
    session["user_email"] = email
    return jsonify({"ok": True, "email": email})


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/progress")
@require_login
def get_progress():
    """Retorna o estado atual de progresso do download."""
    with _progress_lock:
        return jsonify(dict(progress_state))


@app.post("/api/download")
@require_login
def download_videos():
    """
    Endpoint que recebe uma lista de URLs do YouTube e faz o download
    usando yt_dlp, salvando na pasta ./downloads.
    Também atualiza um estado de progresso que o front pode consultar.
    """
    if not _rate_limit_download():
        return jsonify({"error": "Muitas solicitações. Aguarde um minuto e tente de novo."}), 429

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Corpo da requisição inválido."}), 400

    urls, err = _sanitize_urls(data.get("urls") or [])
    if err:
        return jsonify({"error": err}), 400

    audio_only = bool(data.get("audioOnly"))

    # Garante que a pasta de downloads exista
    # Usa a pasta padrão "Downloads" do usuário no Windows
    user_home = os.path.expanduser("~")
    downloads_dir = os.path.join(user_home, "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    total_videos = len(urls)

    with _progress_lock:
        if progress_state.get("status") == "downloading":
            return jsonify({"error": "Já existe um download em andamento. Aguarde terminar."}), 409
        progress_state.update(
            {
                "status": "downloading",
                "percent": 0,
                "current_video": None,
                "current_video_percent": 0,
                "index": 0,
                "total": total_videos,
                "message": f"Iniciando download de {total_videos} vídeo(s)...",
            }
        )

    def make_hook(video_index: int, total: int, url: str):
        """Cria um hook de progresso para um vídeo específico."""

        def hook(d):
            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes") or 0
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

                if total_bytes > 0:
                    file_percent = int(downloaded * 100 / total_bytes)
                else:
                    file_percent = 0

                # Progresso geral: vídeos anteriores completos + parte do atual
                overall = ((video_index - 1) + file_percent / 100.0) / total
                overall_percent = int(overall * 100)

                _progress_update(
                    status="downloading",
                    percent=overall_percent,
                    current_video=url,
                    current_video_percent=file_percent,
                    index=video_index,
                    total=total,
                    message=f"Baixando vídeo {video_index}/{total}",
                )

        return hook

    try:
        # Usamos uma instância de YoutubeDL por vídeo para poder trocar o hook
        for idx, url in enumerate(urls, start=1):
            mode_label = "áudio" if audio_only else "vídeo"
            app.logger.info(f"Baixando {mode_label} ({idx}/{total_videos}): {url}")

            # Configurações de download
            # Se audio_only=True, baixa apenas o áudio e converte para MP3.
            if audio_only:
                ydl_opts = {
                    "outtmpl": os.path.join(downloads_dir, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "format": "bestaudio/best",
                    "skip_download": False,
                    "progress_hooks": [make_hook(idx, total_videos, url)],
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            else:
                ydl_opts = {
                    # Salva fora da pasta do projeto, para evitar reload do Live Server
                    "outtmpl": os.path.join(downloads_dir, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                    "skip_download": False,
                    "progress_hooks": [make_hook(idx, total_videos, url)],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        _progress_update(
            status="done",
            percent=100,
            current_video_percent=100,
            message=f"Seus {total_videos} vídeo(s) foram salvos com sucesso! ✅",
        )

        return jsonify(
            {
                "status": "ok",
                "message": f"Seus {total_videos} vídeo(s) foram salvos com sucesso em ~/Downloads! ✅",
                "count": total_videos,
            }
        )
    except Exception as e:
        app.logger.exception("Erro ao baixar vídeos.")
        _progress_update(
            status="error",
            message=_public_error(str(e)) if not DEBUG else f"Erro ao baixar vídeos: {e}",
        )
        return jsonify({"error": _public_error(str(e))}), 500


if __name__ == "__main__":
    # Rode com: python server.py (ou na raiz: python downloader/server.py)
    # HOST/PORT permitem deploy (ex.: PORT em PaaS). FLASK_DEBUG=1 ativa debug.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=DEBUG)
