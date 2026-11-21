#!/usr/bin/env python3
"""إعداد النشر السحابي (Supabase + GitHub + Render) من جهاز المالك.

المفاتيح تُقرأ من مجلد سطح المكتب فقط، ولا تُطبع في الطرفية ولا تُحفظ في المستودع.
التشغيل:  python deploy/setup_cloud.py [supabase|github|render|verify|all]
"""
from __future__ import annotations

import json
import os
import re
import secrets
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
KEYS_DIR = Path(os.environ.get("QIMMA_KEYS", Path.home() / "Desktop" / "QIMMA HUB - الموقع" / "مفاتيح"))
STATE_FILE = ROOT / "deploy" / "cloud-state.json"
REPORT_FILE = ROOT / "deploy" / "تقرير-النشر.txt"

SUPABASE_API = "https://api.supabase.com/v1"
GITHUB_API = "https://api.github.com"
RENDER_API = "https://api.render.com/v1"

PROJECT_NAME = "qimma-hub-site"
SUPABASE_REGION = "eu-central-1"
RENDER_REGION = "frankfurt"
PYTHON_VERSION = "3.12.8"


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str) -> None:
    print("\n[خطأ] " + msg, flush=True)
    sys.exit(1)


def mask(value: str, keep: int = 6) -> str:
    if not value:
        return "(فارغ)"
    if len(value) <= keep * 2:
        return value[0] * 4 + "…"
    return value[:keep] + "…" + value[-4:]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def read_key(filename: str, var: str) -> str:
    path = KEYS_DIR / filename
    if not path.exists():
        die(f"الملف غير موجود: {path}\nأنشئه وضع فيه السطر: {var}=...")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    match = re.search(rf"^{var}\s*[=:]\s*(\S+)\s*$", text, re.MULTILINE)
    if not match:
        die(f"لم أجد {var} داخل {path}")
    value = match.group(1).strip().strip('"\'')
    if value.lower().startswith(("ضع", "صق", "here", "your", "xxx")):
        die(f"القيمة في {path} ما زالت Placeholder. ضع المفتاح الحقيقي.")
    return value


def api(method: str, url: str, token: str, body=None, ok=(200, 201, 204), tries: int = 4,
        accept: str = "application/json") -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "User-Agent": "qimma-hub-deploy",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read()
                payload = None
                if raw:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = raw.decode("utf-8", "replace")
                if resp.status not in ok:
                    die(f"{method} {url} أعاد {resp.status}: {payload}")
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw.strip()
            if exc.code == 429 or exc.code >= 500:
                if attempt < tries:
                    wait = 5 * attempt
                    log(f"  … الخادم مشغول ({exc.code})، إعادة المحاولة بعد {wait} ثانية")
                    time.sleep(wait)
                    continue
            if exc.code in ok:
                return exc.code, payload
            die(f"{method} {url} أعاد {exc.code}: {payload}")
        except urllib.error.URLError as exc:
            if attempt < tries:
                log(f"  … تعذّر الاتصال ({exc.reason})، إعادة المحاولة")
                time.sleep(5 * attempt)
                continue
            die(f"تعذّر الاتصال بالإنترنت: {exc.reason}")
    raise SystemExit(1)


def api_get_all(url: str, token: str, key: str | None = None) -> list:
    """يقرأ صفحات API التي تعيد {items/…, cursor} حتى النهاية."""
    items: list = []
    cursor = None
    while True:
        sep = "&" if "?" in url else "?"
        full = f"{url}{sep}limit=100" + (f"&cursor={cursor}" if cursor else "")
        _, payload = api("GET", full, token)
        if isinstance(payload, list):
            items.extend(payload)
            break
        if isinstance(payload, dict):
            chunk = payload.get(key, payload.get("items", []))
            items.extend(chunk)
            cursor = payload.get("cursor")
            if not cursor or not chunk:
                break
        else:
            break
    if key:
        return [x[key] if isinstance(x, dict) and key in x else x for x in items]
    return items


# ---------------------------------------------------------------- Supabase

def read_optional(filename: str, var: str) -> str:
    path = KEYS_DIR / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    match = re.search(rf"^{var}\s*[=:]\s*(\S+)\s*$", text, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip().strip('"\'')
    if value.lower().startswith(("ضع", "صق", "here", "your", "xxx")):
        return ""
    return value


def step_supabase(state: dict) -> dict:
    token = read_key("supabase.txt", "SUPABASE_ACCESS_TOKEN")
    log(f"Supabase: المفتاح {mask(token)}")

    sb = state.setdefault("supabase", {})
    if sb.get("ref") and sb.get("db_url"):
        log(f"Supabase: المشروع جاهز مسبقاً ({sb['ref']}) — تخطٍّ")
        return state

    project = None
    if sb.get("ref"):
        _, project = api("GET", f"{SUPABASE_API}/projects/{sb['ref']}", token)
    else:
        _, projects = api("GET", f"{SUPABASE_API}/projects", token)
        projects = projects or []
        match = next((p for p in projects if p.get("name") == PROJECT_NAME), None)
        if match:
            project = match
        elif len(projects) == 1:
            project = projects[0]
            log(f"Supabase: المفتاح لا يملك صلاحية إنشاء مشروع؛ سأستخدم المشروع الموجود «{project.get('name')}»")
        elif projects:
            names = "، ".join(p.get("name", "") for p in projects)
            die(f"يوجد أكثر من مشروع ({names}) والمفتاح لا يملك صلاحية اختيار المنظمة.\n"
                "أنشئ توكناً كامل الصلاحية (Full access) أو احذف المشاريع الزائدة.")
        else:
            die("لا يوجد أي مشروع في الحساب، والمفتاح الحالي لا يملك صلاحية إنشاء مشروع.\n"
                "أنشئ مشروعاً من لوحة Supabase أو استخدم توكناً كامل الصلاحية (Full access).")

    ref = project["id"]
    sb["ref"] = ref
    sb["url"] = f"https://{ref}.supabase.co"
    save_state(state)

    db_pass = sb.get("db_pass") or read_optional("supabase.txt", "SUPABASE_DB_PASSWORD")
    if not db_pass:
        alphabet = string.ascii_letters + string.digits
        db_pass = "".join(secrets.choice(alphabet) for _ in range(28))
        log("Supabase: تعيين كلمة مرور جديدة لقاعدة البيانات …")
        api("PATCH", f"{SUPABASE_API}/projects/{ref}/database/password", token, {"password": db_pass})
    sb["db_pass"] = db_pass
    save_state(state)

    # انتظار الجاهزية
    deadline = time.time() + 12 * 60
    status = project.get("status", "")
    while status not in ("ACTIVE_HEALTHY", "ACTIVE_UNHEALTHY"):
        if time.time() > deadline:
            die("انتهت مهلة انتظار تجهيز مشروع Supabase. أعد تشغيل نفس الأمر لاحقاً.")
        time.sleep(15)
        _, current = api("GET", f"{SUPABASE_API}/projects/{ref}", token)
        status = current.get("status", "")
        log(f"  … حالة المشروع: {status}")
    if status != "ACTIVE_HEALTHY":
        die(f"المشروع غير سليم: {status}")

    # مفتاح الخدمة
    _, keys = api("GET", f"{SUPABASE_API}/projects/{ref}/api-keys?reveal=true", token)
    service_key = ""
    for item in keys or []:
        name = str(item.get("name") or item.get("id") or "")
        if name in ("service_role", "secret"):
            service_key = item.get("api_key") or ""
            if name == "service_role":
                break
    if not service_key:
        die("لم أجد مفتاح service_role/secret في مشروع Supabase.")
    sb["service_key"] = service_key

    # رابط التجميع (Pooler)
    _, poolers = api("GET", f"{SUPABASE_API}/projects/{ref}/config/database/pooler", token)
    if not isinstance(poolers, list) or not poolers:
        die("لم أستطع قراءة إعدادات Pooler من Supabase.")
    primary = [p for p in poolers if p.get("database_type") == "PRIMARY"]
    tx = [p for p in primary if p.get("pool_mode") == "transaction"]
    chosen = (tx or primary or poolers)[0]
    user = urllib.parse.quote(str(chosen["db_user"]), safe="")
    password = urllib.parse.quote(db_pass, safe="")
    db_url = (
        f"postgresql://{user}:{password}@{chosen['db_host']}:{chosen['db_port']}/"
        f"{chosen['db_name']}?sslmode=require"
    )
    sb["db_url"] = db_url
    sb["pool_mode"] = chosen.get("pool_mode")

    # التحقق من الاتصال وأن المشروع لا يحتوي جداول غريبة
    expected = {"categories", "services", "templates", "orders",
                "gallery", "faqs", "packages", "settings", "admins"}
    tables: list[str] = []
    last_error = None
    for _ in range(6):
        try:
            import psycopg

            with psycopg.connect(db_url, prepare_threshold=None, autocommit=True,
                                 connect_timeout=20) as con:
                tables = [r[0] for r in con.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ).fetchall()]
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(5)
    else:
        die(f"تعذّر الاتصال بقاعدة بيانات Supabase: {last_error}")

    foreign = sorted(t for t in tables if t not in expected)
    if foreign:
        die("المشروع يحتوي جداول عامة غير خاصة بالموقع: " + ", ".join(foreign)
            + "\nلن ألمسها. استخدم مشروع Supabase فارغاً أو مشروعاً خاصاً بهذا الموقع.")
    sb["existing_tables"] = tables
    save_state(state)
    log(f"Supabase: تم — {sb['url']} (pooler: {chosen.get('pool_mode')}, منفذ {chosen['db_port']}, "
        f"جداول حالية: {len(tables)})")
    return state


# ---------------------------------------------------------------- GitHub

def run_git(args: list[str], quiet: bool = False) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 0:
        die(f"فشل الأمر: git {' '.join(args)}\n{result.stderr.strip()}")
    if not quiet and result.stdout.strip():
        log(result.stdout.strip())


def step_github(state: dict) -> dict:
    token = read_key("github.txt", "GITHUB_TOKEN")
    log(f"GitHub: المفتاح {mask(token)}")

    _, me = api("GET", f"{GITHUB_API}/user", token)
    login = me["login"]
    gh = state.setdefault("github", {"login": login})
    gh["login"] = login

    repo_name = gh.get("repo_name") or PROJECT_NAME
    code, repo = api("GET", f"{GITHUB_API}/repos/{login}/{repo_name}", token, ok=(200, 404))
    if code == 404:
        log(f"GitHub: إنشاء المستودع العام {login}/{repo_name}")
        _, repo = api(
            "POST",
            f"{GITHUB_API}/user/repos",
            token,
            {
                "name": repo_name,
                "description": "QIMMA HUB — مركز القمة للخدمات الجامعية",
                "private": False,
                "has_issues": False,
                "has_wiki": False,
                "has_projects": False,
            },
        )
    else:
        log(f"GitHub: المستودع موجود مسبقاً {login}/{repo_name}")

    repo_url = repo["html_url"].rstrip("/") + ".git"
    gh["repo_url"] = repo_url
    save_state(state)

    if not (ROOT / ".git").exists():
        run_git(["init", "-b", "main"])
    run_git(["config", "user.name", "QIMMA HUB"])
    run_git(["config", "user.email", "qimma.hub@uni.edu.ly"])

    run_git(["add", ".gitignore", "README.md", "requirements.txt", "run.py", "render.yaml",
             "تشغيل-الموقع.bat", "app", "deploy/setup_cloud.py"])

    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                            encoding="utf-8", errors="replace", capture_output=True)
    if status.stdout.strip():
        run_git(["commit", "-m", "نشر أولي لموقع QIMMA HUB مع دعم Supabase وRender"], quiet=True)
        log("GitHub: تم إنشاء commit")
    else:
        log("GitHub: لا تغييرات جديدة للـ commit")

    push_url = f"https://x-access-token:{token}@github.com/{login}/{repo_name}.git"
    log("GitHub: رفع الملفات …")
    run_git(["push", "--force", push_url, "main"], quiet=True)
    subprocess.run(["git", "remote", "remove", "origin"], cwd=ROOT, capture_output=True)
    run_git(["remote", "add", "origin", f"https://github.com/{login}/{repo_name}.git"])
    gh["repo"] = f"{login}/{repo_name}"
    save_state(state)
    log(f"GitHub: تم الرفع إلى https://github.com/{login}/{repo_name}")
    return state


# ---------------------------------------------------------------- Render

def step_render(state: dict) -> dict:
    token = read_key("render.txt", "RENDER_API_KEY")
    log(f"Render: المفتاح {mask(token)}")

    gh = state.get("github", {})
    sb = state.get("supabase", {})
    if not gh.get("repo_url") or not sb.get("db_url"):
        die("أكمل خطوتي Supabase وGitHub أولاً (python deploy/setup_cloud.py all).")

    rn = state.setdefault("render", {})
    if rn.get("service_id"):
        log(f"Render: الخدمة موجودة مسبقاً ({rn['service_id']}) — سأتحقق من حالة النشر فقط")
        return step_render_wait(state, token)

    owners = api_get_all(f"{RENDER_API}/owners", token, "owner")
    owner_id = None
    for item in owners:
        if item.get("type") in (None, "user", "team"):
            owner_id = item.get("id")
            if item.get("type") == "user":
                break
    if not owner_id:
        die("لم أجد Workspace في Render. افتح لوحة Render مرة واحدة ثم أعد المحاولة.")
    log(f"Render: مساحة العمل {owner_id}")

    services = api_get_all(f"{RENDER_API}/services", token, "service")
    existing = next((s for s in services if s.get("name") == PROJECT_NAME), None)
    if existing:
        log(f"Render: الخدمة «{PROJECT_NAME}» موجودة ({existing['id']})")
        rn["service_id"] = existing["id"]
        rn["url"] = (existing.get("serviceDetails") or {}).get("url", "")
        save_state(state)
        return step_render_wait(state, token)

    if not rn.get("secret_key"):
        rn["secret_key"] = secrets.token_hex(32)

    body = {
        "type": "web_service",
        "name": PROJECT_NAME,
        "ownerId": owner_id,
        "repo": gh["repo_url"],
        "branch": "main",
        "autoDeployTrigger": "commit",
        "envVars": [
            {"key": "PYTHON_VERSION", "value": PYTHON_VERSION},
            {"key": "SECRET_KEY", "value": rn["secret_key"]},
            {"key": "DATABASE_URL", "value": sb["db_url"]},
            {"key": "SUPABASE_URL", "value": sb["url"]},
            {"key": "SUPABASE_SERVICE_KEY", "value": sb["service_key"]},
        ],
        "serviceDetails": {
            "env": "python",
            "runtime": "python",
            "plan": "free",
            "region": RENDER_REGION,
            "numInstances": 1,
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
            },
            "healthCheckPath": "/healthz",
        },
    }
    log(f"Render: إنشاء خدمة ويب مجانية في {RENDER_REGION} …")
    _, payload = api("POST", f"{RENDER_API}/services", token, body)
    service = payload.get("service", payload)
    rn["service_id"] = service["id"]
    rn["deploy_id"] = payload.get("deployId", "")
    rn["url"] = (service.get("serviceDetails") or {}).get("url", "")
    save_state(state)
    log(f"Render: الخدمة {rn['service_id']} — بدأ البناء")
    return step_render_wait(state, token)


def step_render_wait(state: dict, token: str) -> dict:
    rn = state["render"]
    sid = rn["service_id"]
    deploy_id = rn.get("deploy_id")
    if not deploy_id:
        _, deploys = api("GET", f"{RENDER_API}/services/{sid}/deploys?limit=1", token)
        if deploys:
            first = deploys[0]
            deploy_id = (first.get("deploy") or first).get("id")
            rn["deploy_id"] = deploy_id

    deadline = time.time() + 20 * 60
    status = "created"
    endpoint = f"{RENDER_API}/services/{sid}/deploys/{deploy_id}"
    while status not in ("live", "build_failed", "update_failed", "canceled", "deactivated"):
        if time.time() > deadline:
            log("Render: انتهت مدة الانتظار. تحقق من اللوحة، ثم شغّل: verify")
            return state
        time.sleep(15)
        try:
            _, deploy = api("GET", endpoint, token)
        except SystemExit:
            raise
        status = (deploy.get("deploy") or deploy).get("status", "")
        log(f"  … حالة النشر: {status}")

    rn["status"] = status
    if status != "live":
        save_state(state)
        die(f"فشل نشر Render: {status}. راجع سجل البناء في لوحة Render.")

    _, service = api("GET", f"{RENDER_API}/services/{sid}", token)
    svc = service.get("service", service)
    rn["url"] = (svc.get("serviceDetails") or {}).get("url", rn.get("url", ""))
    save_state(state)
    log(f"Render: الموقع مباشر على {rn['url']}")
    return state


# ---------------------------------------------------------------- التحقق والإنهاء

def http_ok(url: str, timeout: int = 120) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "qimma-hub-verify"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def step_verify(state: dict) -> dict:
    sb = state.get("supabase", {})
    rn = state.get("render", {})
    if not sb.get("db_url"):
        die("لا توجد بيانات Supabase في cloud-state.json.")
    if not rn.get("url"):
        die("لا يوجد رابط Render بعد. شغّل خطوة render أولاً.")

    base = rn["url"].rstrip("/")
    log(f"التحقق: {base}/healthz")
    status, body = http_ok(f"{base}/healthz")
    if status != 200:
        die(f"الموقع لا يستجيب بعد ({status}). إن كان أول تشغيل فقد يستغرق دقيقة؛ أعد المحاولة.")
    log(f"  … {status} {body.strip()[:200]}")

    for path in ("/", "/services", "/gallery", "/order", "/track", "/admin/login", "/qr.png"):
        code, _ = http_ok(f"{base}{path}")
        log(f"  {path} → {code}")
        if code != 200:
            die(f"الصفحة {path} أعادت {code}")

    # تحديث رابط الموقع داخل قاعدة البيانات ليتوافق رمز QR
    try:
        import psycopg

        with psycopg.connect(sb["db_url"], prepare_threshold=None, autocommit=True) as con:
            con.execute(
                "INSERT INTO settings(key, value) VALUES('site_url', %s) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (base,),
            )
        log("تم تحديث «رابط الموقع» في الإعدادات إلى رابط Render")
    except Exception as exc:  # noqa: BLE001
        log(f"تنبيه: لم أستطع تحديث رابط الموقع تلقائياً ({exc}). حدّثه من لوحة الإدارة.")

    code, _ = http_ok(f"{base}/qr.png")
    log(f"  /qr.png → {code}")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        "تم النشر بنجاح\n"
        "================\n"
        f"الموقع: {base}\n"
        f"لوحة الإدارة: {base}/admin\n"
        "اسم المستخدم: admin\n"
        "كلمة المرور الافتراضية: admin123 — غيّرها فوراً من الإعدادات\n"
        f"قاعدة البيانات: {sb.get('url')}\n"
        f"GitHub: {state.get('github', {}).get('repo_url', '—')}\n"
        "\n"
        "ملاحظات:\n"
        "- رابط Render المجاني يتوقف بعد 15 دقيقة خمول؛ أول زيارة بعده تستغرق 30-60 ثانية.\n"
        "- أي تعديل مستقبلي: ارفع إلى GitHub وسيعاد النشر تلقائياً.\n"
        "- نسخة احتياطية: Supabase ← Database ← Backups (الخطة المجانية تحتفظ بنسخة يومية محدودة).\n",
        encoding="utf-8",
    )
    log(f"تم كتابة التقرير: {REPORT_FILE}")
    return state


def main() -> None:
    step = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if step not in ("supabase", "github", "render", "verify", "all"):
        die("الاستخدام: python deploy/setup_cloud.py [supabase|github|render|verify|all]")

    log(f"مجلد المفاتيح: {KEYS_DIR}")
    state = load_state()

    if step in ("supabase", "all"):
        state = step_supabase(state)
    if step in ("github", "all"):
        state = step_github(state)
    if step in ("render", "all"):
        state = step_render(state)
    if step in ("verify", "all"):
        state = step_verify(state)

    log("\nانتهى.")


if __name__ == "__main__":
    main()
