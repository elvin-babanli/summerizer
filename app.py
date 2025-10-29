# app.py
import os
import uuid
from io import BytesIO
from textwrap import wrap
from datetime import datetime, timedelta
from pathlib import Path
import re

from flask import (
    Flask, request, session, render_template, redirect,
    url_for, flash, jsonify, abort, send_file
)
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import ProductionConfig
from database import db
from models import UserSession
from utils.privacy import hash_ip
from services.openai_client import call_llm  # lazy client-in içində qurulur


# ----------------- Utilities -----------------
def strip_banner(text: str) -> str:
    """Result-un əvvəlindəki [SUMMARY · …] və LLM error sətirlərini silir."""
    if not text:
        return ""
    text = re.sub(r"^\s*\[[^\]\n]+\]\s*\n+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\(LLM error.*\)\s*\n+", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*Showing a minimal fallback.*\n+", "", text, flags=re.IGNORECASE | re.MULTILINE)
    return text.strip()


# ----------------- LLM flag -----------------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
try:
    from openai import OpenAI  # noqa: F401
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


# ===================== Helpers (storage, stats, files) =====================
ALLOWED_EXTS = {".pdf", ".docx", ".txt"}

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTS

def get_dir_size_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    total = 0
    for child in p.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total / (1024 * 1024)

def cleanup_storage(app: Flask):
    """
    RETENTION_HOURS keçmiş sessiya qovluqlarını silir
    və MAX_STORAGE_MB_TOTAL aşılarsa ən köhnələri təmizləyir.
    """
    uploads_dir = Path(app.config["UPLOAD_FOLDER"])
    if not uploads_dir.exists():
        return

    now = datetime.utcnow()
    ttl = timedelta(hours=app.config["RETENTION_HOURS"])

    # 1) Zaman əsaslı təmizləmə
    for bucket_dir in uploads_dir.iterdir():
        if bucket_dir.is_dir():
            try:
                mtime = datetime.utcfromtimestamp(bucket_dir.stat().st_mtime)
                if now - mtime > ttl:
                    for f in bucket_dir.rglob("*"):
                        if f.is_file():
                            f.unlink(missing_ok=True)
                    bucket_dir.rmdir()
            except Exception:
                pass

    # 2) Disk kvotası təmizləmə
    while get_dir_size_mb(uploads_dir) > app.config["MAX_STORAGE_MB_TOTAL"]:
        dirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
        if not dirs:
            break
        oldest = min(dirs, key=lambda d: d.stat().st_mtime)
        try:
            for f in oldest.rglob("*"):
                if f.is_file():
                    f.unlink(missing_ok=True)
            oldest.rmdir()
        except Exception:
            break

def count_pages_saved_file(filepath: Path) -> int:
    """PDF üçün real səhifə sayı, .docx/.txt üçün 1 qaytarır."""
    if not filepath.exists():
        return 0
    if filepath.suffix.lower() == ".pdf":
        try:
            from PyPDF2 import PdfReader
            with open(filepath, "rb") as f:
                reader = PdfReader(f)
                return len(reader.pages)
        except Exception:
            return 0
    return 1

def extract_text_from_file(path: Path, max_chars: int = 50_000) -> str:
    """Fayldan mətni çıxarır (PDF/DOCX/TXT). max_chars ilə kəsir."""
    ext = path.suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            from PyPDF2 import PdfReader
            with open(path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    t = page.extract_text() or ""
                    if t:
                        text += t + "\n"
                    if len(text) >= max_chars:
                        break
        elif ext == ".docx":
            from docx import Document
            doc = Document(path)
            for p in doc.paragraphs:
                if p.text:
                    text += p.text + "\n"
                if len(text) >= max_chars:
                    break
        elif ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(max_chars)
        else:
            return ""
    except Exception:
        return ""
    return text[:max_chars].strip()

def gather_corpus(app: Flask, max_chars_total: int = 80_000) -> tuple[str, list[dict]]:
    """
    Bucketdəki bütün fayllardan mətni birləşdirir.
    Qaytarır: (corpus_text, files_meta)
    """
    bucket = session.get("bucket")
    if not bucket:
        return "", []

    bdir = Path(app.config["UPLOAD_FOLDER"]) / bucket
    if not bdir.exists():
        return "", []

    texts = []
    metas = []
    total = 0

    # Son yüklənənlərdən başlayırıq
    for p in sorted(bdir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or not allowed_file(p.name):
            continue
        remaining = max_chars_total - total
        if remaining <= 0:
            break
        t = extract_text_from_file(p, max_chars=remaining)
        if not t:
            continue
        texts.append(f"# {p.name.split('_',1)[-1]}\n{t}")
        metas.append({
            "name": p.name.split("_", 1)[-1],
            "ext": p.suffix.lower().lstrip("."),
            "pages": count_pages_saved_file(p),
            "size_bytes": p.stat().st_size if p.exists() else 0
        })
        total += len(t)

    return ("\n\n".join(texts)).strip(), metas

def bump_session_stats(bytes_added: int = 0, pages_added: int = 0):
    """Upload/Remove zamanı ölçü və səhifə sayını sessiya qeydinə əlavə/çıxar."""
    try:
        bucket = session.get("bucket")
        if not bucket:
            return
        obj = UserSession.query.filter_by(bucket_uuid=bucket).first()
        if not obj:
            return
        obj.files_count = max(obj.files_count or 0, 0)
        if bytes_added:
            obj.total_bytes = (obj.total_bytes or 0) + int(bytes_added)
            if obj.total_bytes < 0:
                obj.total_bytes = 0
        if pages_added:
            obj.total_pages = (obj.total_pages or 0) + int(pages_added)
            if obj.total_pages < 0:
                obj.total_pages = 0
        db.session.commit()
    except Exception:
        db.session.rollback()

def compute_bucket_stats(app: Flask) -> dict:
    """Cari sessiya bucket-i üçün: files, pages, bytes."""
    bucket = session.get("bucket")
    stats = {"files": 0, "pages": 0, "bytes": 0}
    if not bucket:
        return stats

    bdir = Path(app.config["UPLOAD_FOLDER"]) / bucket
    if bdir.exists():
        for p in bdir.iterdir():
            if p.is_file():
                stats["files"] += 1
                try:
                    stats["bytes"] += p.stat().st_size
                except Exception:
                    pass
                try:
                    stats["pages"] += count_pages_saved_file(p)
                except Exception:
                    pass

    try:
        obj = UserSession.query.filter_by(bucket_uuid=bucket).first()
        if obj:
            stats["files"] = max(stats["files"], obj.files_count or 0)
            stats["pages"] = max(stats["pages"], obj.total_pages or 0)
            stats["bytes"] = max(stats["bytes"], obj.total_bytes or 0)
    except Exception:
        pass

    return stats

def expose_limits(app: Flask) -> dict:
    """Şablona limitləri ötürmək üçün helper."""
    return {
        "max_files": app.config["MAX_FILES"],
        "max_file_mb": app.config["MAX_FILE_MB"],
        "max_total_pages": app.config["MAX_TOTAL_PAGES"],
        "retention_hours": app.config["RETENTION_HOURS"],
        "max_storage_mb_total": app.config["MAX_STORAGE_MB_TOTAL"],
    }

def list_bucket_files(app: Flask) -> list[dict]:
    """
    index.html üçün 'files' siyahısı:
    {id, name, ext, pages, size_bytes}
    """
    bucket = session.get("bucket")
    files = []
    if not bucket:
        return files

    bdir = Path(app.config["UPLOAD_FOLDER"]) / bucket
    if not bdir.exists():
        return files

    for p in sorted(bdir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file():
            continue
        try:
            pages = count_pages_saved_file(p)
        except Exception:
            pages = 0
        try:
            size_b = p.stat().st_size
        except Exception:
            size_b = 0

        files.append({
            "id": p.name,                         # remove üçün identifikator
            "name": p.name.split("_", 1)[-1],     # orijinal adı göstər
            "ext": p.suffix.lower().lstrip("."),
            "pages": pages,
            "size_bytes": size_b,
        })
    return files


# ===================== App Factory =====================
def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(ProductionConfig)

    # --- CSRF / Security ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['WTF_CSRF_SSL_STRICT'] = False         # Referrer məcbur yoxlanmasın
    app.config['WTF_CSRF_CHECK_ORIGIN'] = False       # (istəyə bağlı) origin yoxlaması
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    csrf = CSRFProtect(app)

    # Qovluqlar
    Path("instance").mkdir(exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True, parents=True)

    # DB
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Rate Limit (ENV-dən storage oxu; lokalda memory:// xəbərdarlığı susdurur)
    storage_uri = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri
    )

    # ------------- Session/Bucket & Anon Tracking -------------
    @app.before_request
    def ensure_bucket_and_track():
        # Sessiya bucket
        if "bucket" not in session:
            session["bucket"] = uuid.uuid4().hex
        bucket = session["bucket"]

        # Anonim iz (GDPR-dostu: IP hash, UA string)
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_h = hash_ip(ip, app.config["PRIVACY_SALT"])
        ua = request.headers.get("User-Agent", "")

        obj = UserSession.query.filter_by(bucket_uuid=bucket).first()
        if not obj:
            obj = UserSession(bucket_uuid=bucket, ip_hash=ip_h, user_agent=ua)
            db.session.add(obj)
        else:
            obj.ip_hash = ip_h or obj.ip_hash
            obj.user_agent = ua or obj.user_agent
            obj.last_seen = datetime.utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    # ------------- Security headers -------------
    @app.after_request
    def set_headers(resp):
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        # ⚠️ Referrer-Policy no-referrer DEYIL! CSRF üçün uyğun variant:
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'"
        )
        return resp

    # ------------- Light cleanup before each request -------------
    @app.before_request
    def maybe_cleanup():
        try:
            cleanup_storage(app)
        except Exception:
            pass

    # ===================== Routes =====================
    @app.route("/")
    def index():
        stats = compute_bucket_stats(app)
        limits = expose_limits(app)
        files = list_bucket_files(app)

        # UI defaultları
        options = {
            "task": "summary",
            "words": 800,
            "language": "English",
            "output": "pdf",
            "notes": ""
        }
        languages = ["English", "Azerbaijani", "Turkish", "Russian", "Polish"]
        result_text = session.get("last_result_text", "")

        return render_template(
            "index.html",
            stats=stats,
            limits=limits,
            files=files,
            options=options,
            languages=languages,
            result_text=result_text,
        )

    @app.route("/healthz")
    @csrf.exempt
    def healthz():
        return jsonify(ok=True, time=datetime.utcnow().isoformat())

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/privacy/delete", methods=["POST"])
    def privacy_delete():
        bucket = session.get("bucket")
        if not bucket:
            abort(400, "No active session")

        # DB-də işarələ
        obj = UserSession.query.filter_by(bucket_uuid=bucket).first()
        if obj:
            obj.deleted_at = datetime.utcnow()
            db.session.commit()

        # Faylları sil
        bdir = Path(app.config["UPLOAD_FOLDER"]) / bucket
        if bdir.exists():
            for f in bdir.rglob("*"):
                if f.is_file():
                    f.unlink(missing_ok=True)
            try:
                bdir.rmdir()
            except Exception:
                pass

        # Sessiyanı sıfırla
        session.clear()
        flash("Your data has been deleted.", "success")
        return redirect(url_for("index"))

    @app.route("/reset", methods=["POST"])
    def reset():
        bucket = session.get("bucket")
        if bucket:
            bdir = Path(app.config["UPLOAD_FOLDER"]) / bucket
            if bdir.exists():
                for f in bdir.rglob("*"):
                    if f.is_file():
                        f.unlink(missing_okay=True)
                try:
                    bdir.rmdir()
                except Exception:
                    pass
        session.clear()
        flash("Session reset.", "info")
        return redirect(url_for("index"))

    # ---------- FILE UPLOAD ----------
    @app.route("/upload", methods=["POST"])
    @limiter.limit("10/minute")
    def upload():
        bucket = session.get("bucket")
        if not bucket:
            flash("Session bucket not found.", "error")
            return redirect(url_for("index"))

        bucket_dir = Path(app.config["UPLOAD_FOLDER"]) / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)

        files = request.files.getlist("files")
        if not files or all((f.filename or "").strip() == "" for f in files):
            flash("No files selected.", "error")
            return redirect(url_for("index"))

        # Limitlər
        existing_count = sum(1 for p in bucket_dir.iterdir() if p.is_file())
        max_files = app.config["MAX_FILES"]
        incoming_count = sum(1 for f in files if (f.filename or "").strip() != "")
        if existing_count + incoming_count > max_files:
            flash(f"Too many files. Limit: {max_files}. Remove some or reset.", "error")
            return redirect(url_for("index"))

        max_file_mb = app.config["MAX_FILE_MB"]
        max_total_pages = app.config["MAX_TOTAL_PAGES"]

        pages_this_upload = 0
        saved_any = False

        for f in files:
            filename = (f.filename or "").strip()
            if not filename:
                continue
            if not allowed_file(filename):
                flash(f"Not allowed file type: {filename}", "error")
                continue

            # Faylı saxla (unique adla)
            safe_name = uuid.uuid4().hex + "_" + filename.replace("/", "_").replace("\\", "_")
            target_path = bucket_dir / safe_name
            try:
                f.save(target_path.as_posix())
            except Exception:
                flash(f"Cannot save: {filename}", "error")
                continue

            # Ölçü limiti (MB)
            try:
                size_mb = target_path.stat().st_size / (1024 * 1024)
            except Exception:
                size_mb = 0

            if size_mb > max_file_mb:
                try:
                    target_path.unlink(missing_ok=True)
                except Exception:
                    pass
                flash(f"File too large (> {max_file_mb} MB): {filename}", "error")
                continue

            # Səhifə sayı
            pages = count_pages_saved_file(target_path)
            if pages <= 0:
                try:
                    target_path.unlink(missing_ok=True)
                except Exception:
                    pass
                flash(f"Cannot read pages (corrupt?): {filename}", "error")
                continue

            if pages_this_upload + pages > max_total_pages:
                try:
                    target_path.unlink(missing_ok=True)
                except Exception:
                    pass
                flash(f"Total pages limit exceeded (>{max_total_pages}). '{filename}' skipped.", "error")
                continue

            # Stats
            try:
                bump_session_stats(bytes_added=target_path.stat().st_size, pages_added=pages)
            except Exception:
                pass

            pages_this_upload += pages
            saved_any = True

        if not saved_any:
            return redirect(url_for("index"))

        flash("Files uploaded.", "success")
        return redirect(url_for("index"))

    # ---------- FILE REMOVE ----------
    @app.route("/remove/<path:fid>", methods=["POST"])
    def remove(fid):
        """Bucket içində konkret faylı silir."""
        bucket = session.get("bucket")
        if not bucket:
            flash("No active session.", "error")
            return redirect(url_for("index"))

        target = Path(app.config["UPLOAD_FOLDER"]) / bucket / fid
        if target.exists() and target.is_file():
            try:
                size_b = target.stat().st_size
            except Exception:
                size_b = 0

            try:
                target.unlink(missing_ok=True)
                if size_b:
                    bump_session_stats(bytes_added=-int(size_b), pages_added=0)
                flash("File removed.", "info")
            except Exception:
                flash("Cannot remove this file.", "error")
        else:
            flash("File not found.", "error")

        return redirect(url_for("index"))

    # ---------- GENERATE (real LLM) ----------
    @app.route("/generate", methods=["POST"])
    @limiter.limit("6/minute")
    def generate():
        task = request.form.get("task", "summary")
        words = int(request.form.get("words", "800") or 800)
        language = request.form.get("language", "English")
        output = request.form.get("output", "pdf")
        notes = request.form.get("notes", "")

        # Fayllardan korpus — DÜZGÜN ARGUMENT ADI
        corpus, metas = gather_corpus(app, max_chars_total=120000)
        if not corpus:
            flash("No extracted text from your uploads. Please upload readable files.", "error")
            return redirect(url_for("index"))

        # OpenAI açarı yoxdursa DEMO nəticə ilə davam et
        if not _OPENAI_AVAILABLE or not os.getenv("OPENAI_API_KEY"):
            result_text = (
                f"(Demo mode — please set OPENAI_API_KEY in .env)\n\n"
                f"Task: {task}, Language: {language}, Target: ~{words} words\n\n"
                f"Sources preview:\n{corpus[:1000]}"
            )
        else:
            try:
                # Real LLM cavabı (bizim call_llm modulundan)
                llm_text = call_llm(task=task, words=words, language=language, notes=notes, corpus=corpus)
                result_text = strip_banner(llm_text)
            except Exception as e:
                # LLM error zamanı fallback
                result_text = f"(LLM error: {e})\n\n{corpus[:1200]}"

        # Export üçün sessiyada saxla
        session["export_format"] = output
        session["last_result_text"] = result_text

        # index üçün kontekst
        stats = compute_bucket_stats(app)
        limits = expose_limits(app)
        files = list_bucket_files(app)
        options = {"task": task, "words": words, "language": language, "output": output, "notes": notes}
        languages = ["English", "Azerbaijani", "Turkish", "Russian", "Polish"]

        flash("Generated.", "success")
        return render_template(
            "index.html",
            stats=stats,
            limits=limits,
            files=files,
            options=options,
            languages=languages,
            result_text=result_text,
        )

    # ---------- EXPORT (TXT / PDF / DOCX) ----------
    @app.route("/export", methods=["POST"])
    @limiter.limit("20/hour")
    def export():
        # Form boş gələrsə sessiyadan götür
        raw = request.form.get("result_text")
        result_text = (raw if raw is not None and raw.strip() != "" else session.get("last_result_text", "")).strip()
        result_text = strip_banner(result_text)  # <<< başlıq və errorları burda da təmizlə
        if not result_text:
            flash("Nothing to export.", "error")
            return redirect(url_for("index"))

        # Seçilən formatı götür (form > session > txt)
        fmt = (request.form.get("output") or session.get("export_format") or "txt").lower()
        if fmt not in {"pdf", "docx", "txt"}:
            fmt = "txt"

        bucket = session.get("bucket", "session")
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        if fmt == "pdf":
            # -------- PDF export (reportlab) --------
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            FONT_PATH = os.path.join(app.root_path, "static", "fonts", "DejaVuSans.ttf")
            # Font mövcuddursa register et
            font_name = "Helvetica"
            try:
                if os.path.exists(FONT_PATH):
                    pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))
                    font_name = "DejaVuSans"
            except Exception:
                pass

            bio = BytesIO()
            c = canvas.Canvas(bio, pagesize=A4)
            width, height = A4

            # Marginlər
            left, right = 2 * cm, width - 2 * cm
            top, bottom = height - 2 * cm, 2 * cm
            max_width = right - left
            line_height = 14

            # Mətni sətirlərə böl
            c.setFont(font_name, 11)
            avg_char_w = 5.0
            chars_per_line = max(40, int(max_width / avg_char_w))
            lines = []
            for para in result_text.splitlines():
                if not para.strip():
                    lines.append("")
                else:
                    lines.extend(wrap(para, width=chars_per_line))

            y = top
            for line in lines:
                if y <= bottom:
                    c.showPage()
                    c.setFont(font_name, 11)
                    y = top
                c.drawString(left, y, line)
                y -= line_height

            c.save()
            bio.seek(0)
            fname = f"summary_{bucket[:8]}_{ts}.pdf"
            return send_file(bio, mimetype="application/pdf", as_attachment=True, download_name=fname)

        elif fmt == "docx":
            # -------- DOCX export (python-docx) --------
            from docx import Document
            from docx.shared import Pt

            doc = Document()
            style = doc.styles["Normal"].font
            style.name = "Calibri"
            style.size = Pt(11)

            for block in result_text.split("\n\n"):
                p = doc.add_paragraph()
                lines = block.splitlines()
                if not lines:
                    p.add_run("")
                else:
                    p.add_run(lines[0])
                    for ln in lines[1:]:
                        p.add_run("\n" + ln)

            bio = BytesIO()
            doc.save(bio)
            bio.seek(0)
            fname = f"summary_{bucket[:8]}_{ts}.docx"
            return send_file(
                bio,
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name=fname
            )

        else:
            # -------- TXT export --------
            bio = BytesIO(result_text.encode("utf-8"))
            fname = f"summary_{bucket[:8]}_{ts}.txt"
            return send_file(
                bio,
                mimetype="text/plain; charset=utf-8",
                as_attachment=True,
                download_name=fname
            )

    return app


# ------------------------ LOCAL DEV ENTRY ------------------------
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
