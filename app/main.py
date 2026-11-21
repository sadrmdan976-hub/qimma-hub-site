import csv
import io
import os
import re
import secrets
import uuid
from datetime import datetime
from urllib.parse import quote, urlparse

import segno
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import db, previews, seed, storage
from .auth import hash_password, verify_password

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
MAX_UPLOAD_MB = 15

STATUSES = {
    "new": "جديدة",
    "review": "قيد المراجعة",
    "working": "قيد التنفيذ",
    "ready": "جاهزة للتسليم",
    "done": "مكتملة",
    "cancelled": "ملغاة",
}

DOC_EXT = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx", "ppt", "pptx", "zip", "rar"}
IMG_EXT = {"jpg", "jpeg", "png", "webp"}

app = FastAPI(title="QIMMA HUB", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

templates.env.globals["STATUSES"] = STATUSES
templates.env.globals["KIND_LABELS"] = previews.KIND_LABELS
templates.env.globals["PALETTE_KEYS"] = list(previews.PALETTES.keys())


def fmt_money(value):
    if value is None or value == "":
        return ""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def wa_digits(phone):
    return re.sub(r"\D", "", phone or "")


def media_url(path):
    if not path:
        return ""
    if path.startswith(("http://", "https://", "/")):
        return path
    return "/static/" + path


templates.env.filters["money"] = fmt_money
templates.env.filters["wa"] = wa_digits
templates.env.globals["media"] = media_url


def _secret_key():
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key:
        return env_key
    path = os.path.join(db.DATA_DIR, "secret.key")
    os.makedirs(db.DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(secrets.token_hex(32))
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    if request.url.path.startswith("/static/uploads/orders/") and not request.session.get("admin"):
        return Response(status_code=404)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host", ""):
            return Response(status_code=403)
    return await call_next(request)


# outermost: keeps session available to the guard above
app.add_middleware(SessionMiddleware, secret_key=_secret_key(), same_site="lax", max_age=60 * 60 * 12)


@app.on_event("startup")
def _startup():
    seed.seed()
    for sub in ("templates", "gallery", "orders"):
        os.makedirs(os.path.join(STATIC_DIR, "uploads", sub), exist_ok=True)
    try:
        storage.ensure_buckets()
    except Exception:
        pass


class AuthRedirect(Exception):
    pass


@app.exception_handler(AuthRedirect)
async def _auth_redirect(request: Request, exc: AuthRedirect):
    return RedirectResponse("/admin/login", status_code=303)


def require_admin(request: Request):
    admin = request.session.get("admin")
    if not admin:
        raise AuthRedirect()
    return admin


# ----------------------------------------------------------------- helpers

def site_ctx(request: Request, **extra):
    s = db.get_settings()
    ctx = {
        "request": request,
        "s": s,
        "cats": db.rows("SELECT * FROM categories ORDER BY sort"),
        "path": request.url.path,
        "currency": s.get("currency", "د.ل"),
        "whatsapp": wa_digits(s.get("whatsapp", "")),
        "year": datetime.now().year,
    }
    ctx.update(extra)
    return ctx


def service_cards(limit=None, featured_only=False):
    sql = ("SELECT sv.*, c.name AS category_name, c.slug AS category_slug, "
           "(SELECT COUNT(*) FROM templates t WHERE t.service_id = sv.id AND t.is_active = 1) AS template_count "
           "FROM services sv JOIN categories c ON c.id = sv.category_id WHERE sv.is_active = 1 ")
    if featured_only:
        sql += "AND sv.featured = 1 "
    sql += "ORDER BY c.sort, sv.sort"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.rows(sql)


def categories_with_services():
    out = []
    for cat in db.rows("SELECT * FROM categories ORDER BY sort"):
        services = db.rows(
            "SELECT sv.*, c.slug AS category_slug, "
            "(SELECT COUNT(*) FROM templates t WHERE t.service_id = sv.id AND t.is_active = 1) AS template_count "
            "FROM services sv JOIN categories c ON c.id = sv.category_id "
            "WHERE sv.category_id = ? AND sv.is_active = 1 ORDER BY sv.sort",
            (cat["id"],),
        )
        out.append({"cat": cat, "services": services})
    return out


def get_templates(service_id):
    return db.rows("SELECT * FROM templates WHERE service_id = ? AND is_active = 1 ORDER BY sort, id", (service_id,))


def order_form_data(service_slug="", template_id=None, form=None):
    groups = categories_with_services()
    all_templates = {}
    for item in groups:
        for sv in item["services"]:
            all_templates[sv["id"]] = [
                {"id": t["id"], "title": t["title"], "image": t["image"],
                 "preview": f"/preview/t/{t['id']}.svg"}
                for t in get_templates(sv["id"])
            ]
    selected_service = None
    if service_slug:
        selected_service = db.row("SELECT * FROM services WHERE slug = ? AND is_active = 1", (service_slug,))
    return {
        "groups": groups,
        "all_templates": all_templates,
        "selected_service": selected_service,
        "selected_template": int(template_id) if template_id else None,
        "form": form or {},
    }


CONTENT_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
    "gif": "image/gif", "pdf": "application/pdf", "zip": "application/zip", "rar": "application/vnd.rar",
    "doc": "application/msword", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def save_upload(file: UploadFile, folder, allowed, max_mb=MAX_UPLOAD_MB):
    if file is None or not file.filename:
        return ""
    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in allowed:
        raise ValueError("نوع الملف غير مدعوم. المسموح: " + "، ".join(sorted(allowed)))
    data = file.file.read(max_mb * 1024 * 1024 + 1)
    if len(data) > max_mb * 1024 * 1024:
        raise ValueError(f"حجم الملف أكبر من {max_mb} ميجابايت")
    if storage.enabled():
        try:
            return storage.upload(data, folder, ext, CONTENT_TYPES.get(ext, ""), public=folder != "orders")
        except Exception:
            raise ValueError("تعذّر رفع الملف إلى التخزين السحابي. حاول مرة أخرى.")
    name = f"{uuid.uuid4().hex}.{ext}"
    target_dir = os.path.join(STATIC_DIR, "uploads", folder)
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, name), "wb") as fh:
        fh.write(data)
    return f"uploads/{folder}/{name}"


def new_ref():
    day = datetime.now().strftime("%Y%m%d")
    n = db.scalar("SELECT COUNT(*) FROM orders WHERE ref LIKE ?", (f"QH-{day}-%",), 0)
    return f"QH-{day}-{n + 1:03d}"


def order_wa_text(order, s):
    lines = [
        "طلب جديد عبر موقع QIMMA HUB",
        f"رقم الطلب: {order['ref']}",
        f"الاسم: {order['customer_name']}",
        f"الهاتف: {order['phone']}",
        f"الخدمة: {order['service_name'] or '-'}",
        f"القالب: {order['template_name'] or 'بدون قالب محدد'}",
        f"الكمية: {order['quantity']}",
    ]
    if order["deadline"]:
        lines.append(f"الموعد المطلوب: {order['deadline']}")
    if order["notes"]:
        lines.append(f"ملاحظات: {order['notes']}")
    if order["quote"]:
        lines.append(f"السعر المقدر: {fmt_money(order['quote'])} {s.get('currency', 'د.ل')}")
    return "\n".join(lines)


def wa_link(number, text):
    return f"https://wa.me/{wa_digits(number)}?text={quote(text)}"


# ----------------------------------------------------------------- public

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    featured = service_cards(limit=8, featured_only=True)
    if len(featured) < 4:
        featured = service_cards(limit=8)
    cats = []
    for cat in db.rows("SELECT * FROM categories ORDER BY sort"):
        count = db.scalar("SELECT COUNT(*) FROM services WHERE category_id = ? AND is_active = 1", (cat["id"],), 0)
        cats.append({"cat": cat, "count": count})
    return templates.TemplateResponse(request, "home.html", site_ctx(
        request,
        featured=featured,
        cats_with_counts=cats,
        gallery=db.rows("SELECT * FROM gallery WHERE is_active = 1 ORDER BY sort LIMIT 8"),
        packages=db.rows("SELECT * FROM packages WHERE is_active = 1 ORDER BY sort LIMIT 3"),
        faqs=db.rows("SELECT * FROM faqs WHERE is_active = 1 ORDER BY sort LIMIT 4"),
    ))


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    stats = {
        "services": db.scalar("SELECT COUNT(*) FROM services WHERE is_active = 1", default=0),
        "orders": db.scalar("SELECT COUNT(*) FROM orders", default=0),
        "templates": db.scalar("SELECT COUNT(*) FROM templates WHERE is_active = 1", default=0),
        "categories": db.scalar("SELECT COUNT(*) FROM categories", default=0),
    }
    return templates.TemplateResponse(request, "about.html", site_ctx(request, stats=stats))


@app.get("/services", response_class=HTMLResponse)
def services_page(request: Request):
    return templates.TemplateResponse(request, "services.html", site_ctx(request, groups=categories_with_services()))


@app.get("/services/{slug}", response_class=HTMLResponse)
def service_detail(request: Request, slug: str):
    sv = db.row(
        "SELECT sv.*, c.name AS category_name, c.slug AS category_slug, c.id AS cat_id "
        "FROM services sv JOIN categories c ON c.id = sv.category_id WHERE sv.slug = ? AND sv.is_active = 1",
        (slug,),
    )
    if not sv:
        raise HTTPException(status_code=404)
    related = db.rows(
        "SELECT sv.*, c.slug AS category_slug, "
        "(SELECT COUNT(*) FROM templates t WHERE t.service_id = sv.id AND t.is_active = 1) AS template_count "
        "FROM services sv JOIN categories c ON c.id = sv.category_id "
        "WHERE sv.category_id = ? AND sv.id != ? AND sv.is_active = 1 ORDER BY sv.sort LIMIT 3",
        (sv["cat_id"], sv["id"]),
    )
    return templates.TemplateResponse(request, "service_detail.html", site_ctx(
        request, sv=sv, tpls=get_templates(sv["id"]), related=related,
    ))


@app.get("/gallery", response_class=HTMLResponse)
def gallery_page(request: Request, category: str = ""):
    items = db.rows("SELECT * FROM gallery WHERE is_active = 1 ORDER BY sort, id")
    cats = sorted({g["category"] for g in items if g["category"]})
    if category:
        items = [g for g in items if g["category"] == category]
    return templates.TemplateResponse(request, "gallery.html", site_ctx(
        request, items=items, cats=cats, active_cat=category,
    ))


@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(request, "pricing.html", site_ctx(
        request,
        groups=categories_with_services(),
        packages=db.rows("SELECT * FROM packages WHERE is_active = 1 ORDER BY sort"),
    ))


@app.get("/order", response_class=HTMLResponse)
def order_page(request: Request, service: str = "", template: int = 0):
    data = order_form_data(service_slug=service, template_id=template or None)
    return templates.TemplateResponse(request, "order.html", site_ctx(request, **data))


@app.post("/order", response_class=HTMLResponse)
def order_submit(
    request: Request,
    customer_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    service_id: int = Form(0),
    template_id: int = Form(0),
    quantity: int = Form(1),
    deadline: str = Form(""),
    notes: str = Form(""),
    website: str = Form(""),
    attachment: UploadFile = File(None),
):
    values = dict(customer_name=customer_name.strip(), phone=phone.strip(), email=email.strip(),
                  service_id=service_id, template_id=template_id, quantity=quantity,
                  deadline=deadline.strip(), notes=notes.strip())
    errors = []
    if website.strip():
        errors.append("تم رفض الطلب.")
    if len(customer_name.strip()) < 2:
        errors.append("يرجى كتابة الاسم الكامل.")
    digits = wa_digits(phone)
    if len(digits) < 8 or len(digits) > 15:
        errors.append("يرجى كتابة رقم هاتف صحيح.")
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("البريد الإلكتروني غير صحيح.")
    sv = db.row("SELECT * FROM services WHERE id = ? AND is_active = 1", (service_id,))
    if not sv:
        errors.append("يرجى اختيار الخدمة المطلوبة.")
    if quantity < 1 or quantity > 500:
        errors.append("الكمية يجب أن تكون بين 1 و 500.")
    if len(notes) > 3000:
        errors.append("الملاحظات طويلة جداً.")
    tpl = None
    if template_id:
        tpl = db.row("SELECT * FROM templates WHERE id = ? AND service_id = ?", (template_id, service_id))
        if not tpl:
            errors.append("القالب المختار لا يتبع الخدمة المحددة.")

    saved_file = ""
    if not errors and attachment is not None and attachment.filename:
        try:
            saved_file = save_upload(attachment, "orders", DOC_EXT)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        data = order_form_data(
            service_slug=sv["slug"] if sv else "",
            template_id=template_id or None,
            form=values,
        )
        return templates.TemplateResponse(
            request, "order.html",
            site_ctx(request, **data, errors=errors, order_form=values),
            status_code=422,
        )

    now = datetime.now().isoformat(timespec="seconds")
    ref = new_ref()
    for _ in range(5):
        try:
            db.execute(
                "INSERT INTO orders(ref, customer_name, phone, email, service_id, service_name, template_id, template_name, "
                "quantity, deadline, notes, attachment, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ref, values["customer_name"], values["phone"], values["email"], sv["id"], sv["name"],
                 tpl["id"] if tpl else None, tpl["title"] if tpl else "", quantity, values["deadline"],
                 values["notes"], saved_file, "new", now, now),
            )
            break
        except Exception:
            ref = ref[:-3] + f"{int(ref[-3:]) + 1:03d}"
    return RedirectResponse(f"/order/success/{ref}", status_code=303)


@app.get("/order/success/{ref}", response_class=HTMLResponse)
def order_success(request: Request, ref: str):
    order = db.row("SELECT * FROM orders WHERE ref = ?", (ref,))
    if not order:
        raise HTTPException(status_code=404)
    s = db.get_settings()
    wa = ""
    if s.get("whatsapp"):
        wa = wa_link(s["whatsapp"], order_wa_text(order, s))
    return templates.TemplateResponse(request, "order_success.html", site_ctx(request, order=order, wa_link=wa))


@app.get("/track", response_class=HTMLResponse)
def track(request: Request, ref: str = ""):
    order = None
    not_found = False
    if ref.strip():
        order = db.row("SELECT * FROM orders WHERE ref = ?", (ref.strip().upper(),))
        not_found = order is None
    return templates.TemplateResponse(request, "track.html", site_ctx(
        request, ref=ref.strip().upper(), order=order, not_found=not_found,
    ))


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", site_ctx(request))


@app.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request):
    return templates.TemplateResponse(request, "faq.html", site_ctx(
        request, faqs=db.rows("SELECT * FROM faqs WHERE is_active = 1 ORDER BY sort"),
    ))


@app.get("/preview/t/{tid}.svg")
def template_preview(tid: int):
    t = db.row("SELECT * FROM templates WHERE id = ?", (tid,))
    if not t:
        raise HTTPException(status_code=404)
    return Response(previews.svg(t["kind"], t["palette"], t["title"]),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/preview/g/{gid}.svg")
def gallery_preview(gid: int):
    g = db.row("SELECT * FROM gallery WHERE id = ?", (gid,))
    if not g:
        raise HTTPException(status_code=404)
    return Response(previews.svg(g["kind"], g["palette"], g["title"]),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/qr.png")
def qr_png(request: Request):
    s = db.get_settings()
    url = (s.get("site_url") or str(request.base_url)).strip()
    qr = segno.make(url, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10, border=2, dark="#0A1D35", light="#FFFFFF")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=600"})


# ----------------------------------------------------------------- admin

def admin_ctx(request: Request, **extra):
    base = site_ctx(request)
    base.update({
        "admin": request.session.get("admin", ""),
        "new_orders": db.scalar("SELECT COUNT(*) FROM orders WHERE status = 'new'", default=0),
        "badge": base.get("msg", ""),
    })
    base.update(extra)
    return base


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "admin/login.html", site_ctx(
        request, password_default=db.get_setting("password_changed", "0") != "1",
    ))


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request, username: str = Form(""), password: str = Form("")):
    fails = request.session.get("login_fails", 0)
    if fails >= 8:
        return templates.TemplateResponse(request, "admin/login.html",
                                          site_ctx(request, error="تم إيقاف المحاولات مؤقتاً. أعد تشغيل الخادم أو انتظر قليلاً."),
                                          status_code=429)
    admin = db.row("SELECT * FROM admins WHERE username = ?", (username.strip(),))
    if not admin or not verify_password(password, admin["password_hash"]):
        request.session["login_fails"] = fails + 1
        return templates.TemplateResponse(request, "admin/login.html",
                                          site_ctx(request, error="اسم المستخدم أو كلمة المرور غير صحيحة.", username=username),
                                          status_code=401)
    request.session.clear()
    request.session["admin"] = admin["username"]
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/logout")
def admin_logout(request: Request, admin: str = Depends(require_admin)):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin: str = Depends(require_admin)):
    counts = {r["status"]: r["n"] for r in db.rows("SELECT status, COUNT(*) n FROM orders GROUP BY status")}
    today = datetime.now().strftime("%Y-%m-%d")
    stats = dict(
        total=db.scalar("SELECT COUNT(*) FROM orders", default=0),
        today=db.scalar("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (today + "%",), 0),
        new=counts.get("new", 0),
        working=counts.get("working", 0) + counts.get("review", 0),
        done=counts.get("done", 0),
        services=db.scalar("SELECT COUNT(*) FROM services WHERE is_active = 1", default=0),
    )
    recent = db.rows("SELECT * FROM orders ORDER BY id DESC LIMIT 8")
    return templates.TemplateResponse(request, "admin/dashboard.html", admin_ctx(
        request, stats=stats, recent=recent, counts=counts,
        password_default=db.get_setting("password_changed", "0") != "1",
    ))


@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request, status: str = "", q: str = "", admin: str = Depends(require_admin)):
    sql = "SELECT * FROM orders WHERE 1=1 "
    params = []
    if status in STATUSES:
        sql += "AND status = ? "
        params.append(status)
    if q.strip():
        sql += "AND (ref LIKE ? OR customer_name LIKE ? OR phone LIKE ? OR service_name LIKE ?) "
        like = f"%{q.strip()}%"
        params += [like, like, like, like]
    sql += "ORDER BY id DESC LIMIT 300"
    counts = {r["status"]: r["n"] for r in db.rows("SELECT status, COUNT(*) n FROM orders GROUP BY status")}
    return templates.TemplateResponse(request, "admin/orders.html", admin_ctx(
        request, orders=db.rows(sql, params), f_status=status, q=q,
        counts=counts, total_all=sum(counts.values()),
    ))


@app.get("/admin/orders.csv")
def admin_orders_csv(request: Request, admin: str = Depends(require_admin)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["الرقم", "الاسم", "الهاتف", "البريد", "الخدمة", "القالب", "الكمية", "الموعد",
                     "الحالة", "السعر", "التاريخ", "ملاحظات", "ملاحظات الإدارة"])
    for o in db.rows("SELECT * FROM orders ORDER BY id DESC"):
        writer.writerow([o["ref"], o["customer_name"], o["phone"], o["email"], o["service_name"],
                         o["template_name"], o["quantity"], o["deadline"], STATUSES.get(o["status"], o["status"]),
                         o["quote"] or "", o["created_at"], o["notes"], o["admin_note"]])
    data = "\ufeff" + buf.getvalue()
    return Response(data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=qimma-orders.csv"})


@app.get("/admin/orders/{oid}", response_class=HTMLResponse)
def admin_order_detail(request: Request, oid: int, admin: str = Depends(require_admin)):
    order = db.row("SELECT * FROM orders WHERE id = ?", (oid,))
    if not order:
        raise HTTPException(status_code=404)
    s = db.get_settings()
    wa = ""
    if order["phone"]:
        wa = wa_link(order["phone"], order_wa_text(order, s))
    attachment_url = ""
    if order["attachment"]:
        if order["attachment"].startswith(storage.SB_PREFIX):
            try:
                attachment_url = storage.signed_url(order["attachment"]) or ""
            except Exception:
                attachment_url = ""
        else:
            attachment_url = "/static/" + order["attachment"]
    return templates.TemplateResponse(request, "admin/order.html", admin_ctx(
        request, order=order, wa=wa, attachment_url=attachment_url,
    ))


@app.post("/admin/orders/{oid}")
def admin_order_update(request: Request, oid: int, status: str = Form("new"), quote: str = Form(""),
                       admin_note: str = Form(""), admin: str = Depends(require_admin)):
    if not db.row("SELECT id FROM orders WHERE id = ?", (oid,)):
        raise HTTPException(status_code=404)
    if status not in STATUSES:
        status = "new"
    try:
        quote_val = float(quote) if quote.strip() else None
    except ValueError:
        quote_val = None
    db.execute("UPDATE orders SET status = ?, quote = ?, admin_note = ?, updated_at = ? WHERE id = ?",
               (status, quote_val, admin_note.strip(), datetime.now().isoformat(timespec="seconds"), oid))
    return RedirectResponse(f"/admin/orders/{oid}?msg=saved", status_code=303)


@app.get("/admin/services", response_class=HTMLResponse)
def admin_services(request: Request, admin: str = Depends(require_admin)):
    groups = []
    for cat in db.rows("SELECT * FROM categories ORDER BY sort"):
        rows = db.rows(
            "SELECT sv.*, (SELECT COUNT(*) FROM templates t WHERE t.service_id = sv.id) AS template_count "
            "FROM services sv WHERE sv.category_id = ? ORDER BY sv.sort", (cat["id"],))
        groups.append({"cat": cat, "services": rows})
    return templates.TemplateResponse(request, "admin/services.html", admin_ctx(request, groups=groups))


@app.get("/admin/services/new", response_class=HTMLResponse)
def admin_service_new(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/service_form.html", admin_ctx(
        request, sv=None, cats=db.rows("SELECT * FROM categories ORDER BY sort"), tpls=[],
    ))


@app.get("/admin/services/{sid}", response_class=HTMLResponse)
def admin_service_edit(request: Request, sid: int, admin: str = Depends(require_admin)):
    sv = db.row("SELECT * FROM services WHERE id = ?", (sid,))
    if not sv:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/service_form.html", admin_ctx(
        request, sv=sv, cats=db.rows("SELECT * FROM categories ORDER BY sort"),
        tpls=db.rows("SELECT * FROM templates WHERE service_id = ? ORDER BY sort, id", (sid,)),
    ))


def _service_payload(category_id, name, summary, description, price, price_note, unit, delivery_days,
                     is_active, featured, sort):
    return (category_id, name.strip(), summary.strip(), description.strip(), float(price or 0),
            price_note.strip() or "يبدأ من", unit.strip(), int(delivery_days or 1),
            1 if is_active else 0, 1 if featured else 0, int(sort or 0))


@app.post("/admin/services/new")
def admin_service_create(
    request: Request,
    category_id: int = Form(...), name: str = Form(""), summary: str = Form(""), description: str = Form(""),
    price: str = Form("0"), price_note: str = Form("يبدأ من"), unit: str = Form(""),
    delivery_days: int = Form(2), is_active: int = Form(0), featured: int = Form(0), sort: int = Form(0),
    admin: str = Depends(require_admin),
):
    if not name.strip() or not db.row("SELECT id FROM categories WHERE id = ?", (category_id,)):
        raise HTTPException(status_code=400)
    slug = "service"
    n = 1
    while db.row("SELECT id FROM services WHERE slug = ?", (slug,)):
        n += 1
        slug = f"service-{n}"
    new_id = db.execute(
        "INSERT INTO services(category_id, name, slug, summary, description, price, price_note, unit, "
        "delivery_days, is_active, featured, sort) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (category_id, name.strip(), slug, summary.strip(), description.strip(), float(price or 0),
         price_note.strip() or "يبدأ من", unit.strip(), int(delivery_days or 1),
         1 if is_active else 0, 1 if featured else 0, int(sort or 0)),
    )
    return RedirectResponse(f"/admin/services/{new_id}?msg=saved", status_code=303)


@app.post("/admin/services/{sid}")
def admin_service_update(
    request: Request, sid: int,
    category_id: int = Form(...), name: str = Form(""), summary: str = Form(""), description: str = Form(""),
    price: str = Form("0"), price_note: str = Form("يبدأ من"), unit: str = Form(""),
    delivery_days: int = Form(2), is_active: int = Form(1), featured: int = Form(0), sort: int = Form(0),
    admin: str = Depends(require_admin),
):
    if not db.row("SELECT id FROM services WHERE id = ?", (sid,)):
        raise HTTPException(status_code=404)
    db.execute(
        "UPDATE services SET category_id=?, name=?, summary=?, description=?, price=?, price_note=?, unit=?, "
        "delivery_days=?, is_active=?, featured=?, sort=? WHERE id=?",
        (*_service_payload(category_id, name, summary, description, price, price_note, unit,
                           delivery_days, is_active, featured, sort), sid),
    )
    return RedirectResponse(f"/admin/services/{sid}?msg=saved", status_code=303)


@app.post("/admin/services/{sid}/delete")
def admin_service_delete(request: Request, sid: int, admin: str = Depends(require_admin)):
    for t in db.rows("SELECT * FROM templates WHERE service_id = ?", (sid,)):
        if t["image"]:
            _remove_upload(t["image"])
    db.execute("DELETE FROM templates WHERE service_id = ?", (sid,))
    db.execute("DELETE FROM services WHERE id = ?", (sid,))
    return RedirectResponse("/admin/services?msg=deleted", status_code=303)


@app.post("/admin/services/{sid}/templates")
def admin_template_add(
    request: Request, sid: int,
    title: str = Form(""), kind: str = Form("poster"), palette: str = Form("navy"),
    sort: int = Form(0), image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    if not db.row("SELECT id FROM services WHERE id = ?", (sid,)):
        raise HTTPException(status_code=404)
    if not title.strip():
        return RedirectResponse(f"/admin/services/{sid}?msg=error", status_code=303)
    if kind not in previews.RENDERERS:
        kind = "poster"
    if palette not in previews.PALETTES:
        palette = "navy"
    image_path = ""
    if image is not None and image.filename:
        try:
            image_path = save_upload(image, "templates", IMG_EXT, max_mb=8)
        except ValueError:
            return RedirectResponse(f"/admin/services/{sid}?msg=error", status_code=303)
    db.execute("INSERT INTO templates(service_id, title, kind, palette, image, sort) VALUES(?,?,?,?,?,?)",
               (sid, title.strip(), kind, palette, image_path, int(sort or 0)))
    return RedirectResponse(f"/admin/services/{sid}?msg=saved", status_code=303)


@app.post("/admin/templates/{tid}/delete")
def admin_template_delete(request: Request, tid: int, admin: str = Depends(require_admin)):
    t = db.row("SELECT * FROM templates WHERE id = ?", (tid,))
    if t:
        db.execute("DELETE FROM templates WHERE id = ?", (tid,))
        if t["image"]:
            _remove_upload(t["image"])
    return RedirectResponse(f"/admin/services/{t['service_id']}?msg=deleted" if t else "/admin/services", status_code=303)


def _remove_upload(rel_path):
    if not rel_path:
        return
    if storage.enabled() and (rel_path.startswith(storage.SB_PREFIX) or rel_path.startswith(storage.SUPABASE_URL + "/")):
        storage.delete(rel_path)
        return
    try:
        full = os.path.normpath(os.path.join(STATIC_DIR, rel_path))
        if full.startswith(os.path.normpath(os.path.join(STATIC_DIR, "uploads"))) and os.path.exists(full):
            os.remove(full)
    except OSError:
        pass


@app.get("/admin/gallery", response_class=HTMLResponse)
def admin_gallery(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/gallery.html", admin_ctx(
        request, items=db.rows("SELECT * FROM gallery ORDER BY sort, id")))


@app.get("/admin/gallery/new", response_class=HTMLResponse)
def admin_gallery_new(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/gallery_form.html", admin_ctx(request, item=None))


@app.get("/admin/gallery/{gid}", response_class=HTMLResponse)
def admin_gallery_edit(request: Request, gid: int, admin: str = Depends(require_admin)):
    item = db.row("SELECT * FROM gallery WHERE id = ?", (gid,))
    if not item:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/gallery_form.html", admin_ctx(request, item=item))


def _gallery_payload(title, kind, palette, category, sort, is_active):
    return (title.strip(), kind, palette, category.strip(), int(sort or 0), 1 if is_active else 0)


@app.post("/admin/gallery/new")
def admin_gallery_create(
    request: Request, title: str = Form(""), kind: str = Form("poster"), palette: str = Form("navy"),
    category: str = Form(""), sort: int = Form(0), is_active: int = Form(0), image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    if not title.strip():
        raise HTTPException(status_code=400)
    if kind not in previews.RENDERERS:
        kind = "poster"
    if palette not in previews.PALETTES:
        palette = "navy"
    image_path = ""
    if image is not None and image.filename:
        try:
            image_path = save_upload(image, "gallery", IMG_EXT, max_mb=8)
        except ValueError:
            return RedirectResponse("/admin/gallery?msg=error", status_code=303)
    db.execute("INSERT INTO gallery(title, kind, palette, category, sort, is_active, image) VALUES(?,?,?,?,?,?,?)",
               (*_gallery_payload(title, kind, palette, category, sort, is_active), image_path))
    return RedirectResponse("/admin/gallery?msg=saved", status_code=303)


@app.post("/admin/gallery/{gid}")
def admin_gallery_update(
    request: Request, gid: int, title: str = Form(""), kind: str = Form("poster"), palette: str = Form("navy"),
    category: str = Form(""), sort: int = Form(0), is_active: int = Form(1), image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    item = db.row("SELECT * FROM gallery WHERE id = ?", (gid,))
    if not item:
        raise HTTPException(status_code=404)
    image_path = item["image"]
    if image is not None and image.filename:
        try:
            image_path = save_upload(image, "gallery", IMG_EXT, max_mb=8)
            if item["image"]:
                _remove_upload(item["image"])
        except ValueError:
            return RedirectResponse(f"/admin/gallery/{gid}?msg=error", status_code=303)
    db.execute("UPDATE gallery SET title=?, kind=?, palette=?, category=?, sort=?, is_active=?, image=? WHERE id=?",
               (*_gallery_payload(title, kind, palette, category, sort, is_active), image_path, gid))
    return RedirectResponse(f"/admin/gallery/{gid}?msg=saved", status_code=303)


@app.post("/admin/gallery/{gid}/delete")
def admin_gallery_delete(request: Request, gid: int, admin: str = Depends(require_admin)):
    item = db.row("SELECT * FROM gallery WHERE id = ?", (gid,))
    if item:
        db.execute("DELETE FROM gallery WHERE id = ?", (gid,))
        if item["image"]:
            _remove_upload(item["image"])
    return RedirectResponse("/admin/gallery?msg=deleted", status_code=303)


@app.get("/admin/faqs", response_class=HTMLResponse)
def admin_faqs(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/faqs.html", admin_ctx(
        request, faqs=db.rows("SELECT * FROM faqs ORDER BY sort, id")))


@app.get("/admin/faqs/new", response_class=HTMLResponse)
def admin_faq_new(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/faq_form.html", admin_ctx(request, faq=None))


@app.get("/admin/faqs/{fid}", response_class=HTMLResponse)
def admin_faq_edit(request: Request, fid: int, admin: str = Depends(require_admin)):
    faq = db.row("SELECT * FROM faqs WHERE id = ?", (fid,))
    if not faq:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/faq_form.html", admin_ctx(request, faq=faq))


@app.post("/admin/faqs/new")
def admin_faq_create(request: Request, question: str = Form(""), answer: str = Form(""),
                     sort: int = Form(0), is_active: int = Form(0), admin: str = Depends(require_admin)):
    if not question.strip() or not answer.strip():
        raise HTTPException(status_code=400)
    db.execute("INSERT INTO faqs(question, answer, sort, is_active) VALUES(?,?,?,?)",
               (question.strip(), answer.strip(), int(sort or 0), 1 if is_active else 0))
    return RedirectResponse("/admin/faqs?msg=saved", status_code=303)


@app.post("/admin/faqs/{fid}")
def admin_faq_update(request: Request, fid: int, question: str = Form(""), answer: str = Form(""),
                     sort: int = Form(0), is_active: int = Form(0), admin: str = Depends(require_admin)):
    if not db.row("SELECT id FROM faqs WHERE id = ?", (fid,)):
        raise HTTPException(status_code=404)
    db.execute("UPDATE faqs SET question=?, answer=?, sort=?, is_active=? WHERE id=?",
               (question.strip(), answer.strip(), int(sort or 0), 1 if is_active else 0, fid))
    return RedirectResponse(f"/admin/faqs/{fid}?msg=saved", status_code=303)


@app.post("/admin/faqs/{fid}/delete")
def admin_faq_delete(request: Request, fid: int, admin: str = Depends(require_admin)):
    db.execute("DELETE FROM faqs WHERE id = ?", (fid,))
    return RedirectResponse("/admin/faqs?msg=deleted", status_code=303)


@app.get("/admin/packages", response_class=HTMLResponse)
def admin_packages(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/packages.html", admin_ctx(
        request, packages=db.rows("SELECT * FROM packages ORDER BY sort, id")))


@app.get("/admin/packages/new", response_class=HTMLResponse)
def admin_package_new(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/package_form.html", admin_ctx(request, pkg=None))


@app.get("/admin/packages/{pid}", response_class=HTMLResponse)
def admin_package_edit(request: Request, pid: int, admin: str = Depends(require_admin)):
    pkg = db.row("SELECT * FROM packages WHERE id = ?", (pid,))
    if not pkg:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/package_form.html", admin_ctx(request, pkg=pkg))


def _package_payload(name, tagline, price, old_price, features, featured, sort, is_active):
    try:
        old = float(old_price) if str(old_price).strip() else None
    except ValueError:
        old = None
    return (name.strip(), tagline.strip(), float(price or 0), old, features.strip(),
            1 if featured else 0, int(sort or 0), 1 if is_active else 0)


@app.post("/admin/packages/new")
def admin_package_create(request: Request, name: str = Form(""), tagline: str = Form(""), price: str = Form("0"),
                         old_price: str = Form(""), features: str = Form(""), featured: int = Form(0),
                         sort: int = Form(0), is_active: int = Form(0), admin: str = Depends(require_admin)):
    if not name.strip():
        raise HTTPException(status_code=400)
    db.execute("INSERT INTO packages(name, tagline, price, old_price, features, featured, sort, is_active) "
               "VALUES(?,?,?,?,?,?,?,?)",
               _package_payload(name, tagline, price, old_price, features, featured, sort, is_active))
    return RedirectResponse("/admin/packages?msg=saved", status_code=303)


@app.post("/admin/packages/{pid}")
def admin_package_update(request: Request, pid: int, name: str = Form(""), tagline: str = Form(""),
                         price: str = Form("0"), old_price: str = Form(""), features: str = Form(""),
                         featured: int = Form(0), sort: int = Form(0), is_active: int = Form(0),
                         admin: str = Depends(require_admin)):
    if not db.row("SELECT id FROM packages WHERE id = ?", (pid,)):
        raise HTTPException(status_code=404)
    db.execute("UPDATE packages SET name=?, tagline=?, price=?, old_price=?, features=?, featured=?, sort=?, is_active=? "
               "WHERE id=?", (*_package_payload(name, tagline, price, old_price, features, featured, sort, is_active), pid))
    return RedirectResponse(f"/admin/packages/{pid}?msg=saved", status_code=303)


@app.post("/admin/packages/{pid}/delete")
def admin_package_delete(request: Request, pid: int, admin: str = Depends(require_admin)):
    db.execute("DELETE FROM packages WHERE id = ?", (pid,))
    return RedirectResponse("/admin/packages?msg=deleted", status_code=303)


SETTING_FIELDS = [
    "site_name", "site_name_ar", "tagline", "hero_title", "hero_sub", "about_text",
    "whatsapp", "phone", "email", "facebook", "instagram", "address", "hours", "site_url", "currency",
]


@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request, admin: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/settings.html", admin_ctx(
        request, password_default=db.get_setting("password_changed", "0") != "1",
    ))


@app.post("/admin/settings")
async def admin_settings_save(request: Request, admin: str = Depends(require_admin)):
    form = await request.form()
    for key in SETTING_FIELDS:
        if key in form:
            db.set_setting(key, str(form[key]).strip())
    return RedirectResponse("/admin/settings?msg=saved", status_code=303)


@app.post("/admin/password")
def admin_password_change(request: Request, current: str = Form(""), new: str = Form(""),
                          confirm: str = Form(""), admin: str = Depends(require_admin)):
    row = db.row("SELECT * FROM admins WHERE username = ?", (admin,))
    if not row or not verify_password(current, row["password_hash"]):
        return RedirectResponse("/admin/settings?msg=badpass", status_code=303)
    if len(new) < 8:
        return RedirectResponse("/admin/settings?msg=shortpass", status_code=303)
    if new != confirm:
        return RedirectResponse("/admin/settings?msg=mismatch", status_code=303)
    db.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (hash_password(new), row["id"]))
    db.set_setting("password_changed", "1")
    return RedirectResponse("/admin/settings?msg=passsaved", status_code=303)


@app.get("/healthz")
def healthz():
    db.scalar("SELECT 1")
    return {"ok": True}
