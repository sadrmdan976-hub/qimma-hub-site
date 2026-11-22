from datetime import datetime

from . import db
from .auth import hash_password

SEED_VERSION = "1"

STYLES = [
    ("أكاديمي", "navy"),
    ("حديث", "royal"),
    ("فاخر", "sand"),
    ("راقٍ", "emerald"),
]

CATEGORIES = [
    {
        "name": "الخدمات الطلابية",
        "slug": "students",
        "icon": "cap",
        "description": "كل ما يحتاجه الطالب في دراسته: عروض، أغلفة، تنسيق بحوث، ملخصات، سير ذاتية وتحويل ملفات.",
        "services": [
            dict(name="تصميم عروض PowerPoint", price=25, days=2, kind="slide", featured=1,
                 summary="عروض تقديمية أنيقة وجاهزة للمناقشة، مع تنسيق النصوص والرسوم والجداول."),
            dict(name="تصميم أغلفة البحوث والتقارير", price=15, days=1, kind="cover",
                 summary="أغلفة أكاديمية مطابقة لشروط الجامعة، بتصميم نظيف وشعار الجهة."),
            dict(name="تنسيق البحوث والمشاريع الجامعية", price=20, days=2, kind="doc",
                 summary="تنسيق كامل للبحث: العناوين، الهوامش، الفهارس، الجداول والمراجع."),
            dict(name="تصميم الملخصات والمذكرات الدراسية", price=15, days=2, kind="doc",
                 summary="ملخصات منظمة وسهلة المراجعة، بتصميم بصري يسهّل الحفظ."),
            dict(name="تصميم الخرائط الذهنية", price=15, days=2, kind="map",
                 summary="خرائط ذهنية واضحة تربط المفاهيم وتختصر المادة قبل الامتحان."),
            dict(name="تصميم السير الذاتية (CV)", price=20, days=2, kind="cv",
                 summary="سيرة ذاتية احترافية بصيغة عربية أو إنجليزية جاهزة للطباعة والإرسال."),
            dict(name="تحويل وتنسيق الملفات إلكترونياً", price=5, days=1, kind="doc",
                 summary="تحويل بين Word وPDF والصور، وضغط الملفات وتجهيزها للإرسال."),
            dict(name="التدريب والإتقان", price=30, days=5, kind="doc", unit="/ دورة", featured=1,
                 summary="دورات تعليمية عملية في Word وExcel وPowerPoint — من الأساسيات إلى المستوى الاحترافي، مع تطبيقات وملفات تدريب.",
                 description="خدمة التدريب والإتقان تقدم دورات تعليمية قصيرة وعملية على برامج Microsoft Office: دورة Word لتنسيق البحوث والتقارير والأغلفة، دورة Excel للجداول والحسابات والرسوم البيانية، ودورة PowerPoint لتصميم العروض التقديمية خطوة بخطوة. تشمل كل دورة تطبيقات عملية وملفات تدريب ومساعدة بعد انتهاء الدورة."),
        ],
    },
    {
        "name": "خدمات الأنشطة الجامعية",
        "slug": "activities",
        "icon": "megaphone",
        "description": "تصميمات متكاملة للفعاليات والندوات والمؤتمرات: إعلانات، دعوات، شهادات وبطاقات.",
        "services": [
            dict(name="تصميم إعلانات الأنشطة والفعاليات", price=20, days=2, kind="poster", featured=1,
                 summary="إعلانات جذابة للأنشطة الطلابية بمقاسات مناسبة للمطبوعات ومنصات التواصل."),
            dict(name="تصميم دعوات الندوات العلمية", price=20, days=2, kind="invitation",
                 summary="دعوات رسمية أنيقة للندوات، بتفاصيل المتحدثين والموعد والمكان."),
            dict(name="تصميم دعوات المؤتمرات وورش العمل", price=25, days=2, kind="invitation",
                 summary="دعوات مؤتمرات وورش عمل بهوية بصرية متكاملة ومقاسات متعددة."),
            dict(name="تصميم شهادات المشاركة والحضور", price=10, days=1, kind="certificate",
                 summary="شهادات مشاركة رسمية بتصميم موحّد، بالإمكان إنتاجها بأعداد كبيرة."),
            dict(name="تصميم شهادات الشكر والتقدير", price=10, days=1, kind="certificate",
                 summary="شهادات شكر وتقدير بلمسة ذهبية رسمية تليق بالجهات والمكرمين."),
            dict(name="تصميم بطاقات تعريف المشاركين", price=8, days=1, kind="card",
                 summary="بطاقات تعريف (بادجات) للمشاركين والمنظمين، جاهزة للطباعة والقص."),
            dict(name="تصميم منشورات الحملات التوعوية", price=15, days=2, kind="poster",
                 summary="منشورات توعوية مدروسة بصرياً تناسب الحملات داخل الحرم الجامعي."),
            dict(name="تصميم جداول الفعاليات والبرامج", price=15, days=1, kind="schedule",
                 summary="جداول زمنية منظمة للفعاليات والبرامج، واضحة للقراءة والطباعة."),
        ],
    },
    {
        "name": "الخدمات الرقمية والتصميمية",
        "slug": "digital",
        "icon": "palette",
        "description": "هويات بصرية، منشورات، دعوات إلكترونية، فيديوهات ترويجية وقوالب رقمية جاهزة.",
        "services": [
            dict(name="تصميم الشعارات والهويات البصرية", price=100, days=4, kind="logo", featured=1,
                 summary="هوية بصرية متكاملة: شعار، ألوان، خطوط، وتطبيقات الهوية الأساسية."),
            dict(name="تصميم المنشورات الجامعية", price=15, days=1, kind="poster",
                 summary="منشورات للمناسبات والإعلانات الجامعية بمقاسات إنستغرام وفيسبوك."),
            dict(name="تصميم أغلفة الصفحات والمنشورات", price=15, days=1, kind="cover",
                 summary="أغلفة صفحات ومنشورات بهوية موحّدة ترفع مستوى الحضور الرقمي."),
            dict(name="تصميم الفيديوهات الترويجية", price=100, days=5, kind="video",
                 summary="فيديو ترويجي قصير للأنشطة والمشاريع، مونتاج وتأثيرات وموسيقى."),
            dict(name="تصميم المقدمات والعروض المتحركة", price=40, days=3, kind="video",
                 summary="مقدمات وانتقالات متحركة للعروض والفعاليات والشاشات."),
            dict(name="تصميم الدعوات الإلكترونية", price=20, days=2, kind="invitation",
                 summary="دعوات إلكترونية أنيقة قابلة للإرسال عبر واتساب أو البريد."),
            dict(name="إنشاء رموز QR وروابط إلكترونية", price=10, days=1, kind="qr",
                 summary="أكواد QR قابلة للطباعة وروابط قصيرة لملفاتك وصفحاتك."),
            dict(name="تصميم قوالب رقمية جاهزة", price=25, days=2, kind="poster",
                 summary="قوالب قابلة للتعديل للشهادات والمنشورات والعروض، بهوية جهتك."),
        ],
    },
    {
        "name": "خدمات الطباعة والتجهيز",
        "slug": "printing",
        "icon": "printer",
        "description": "طباعة بحوث وملصقات وشهادات، وتجهيز كامل لملفات ومطبوعات المشاريع والفعاليات.",
        "services": [
            dict(name="طباعة البحوث والتقارير", price=1, days=1, kind="print", unit="/ صفحة",
                 summary="طباعة عالية الجودة للبحوث والتقارير مع تجليد حسب الطلب."),
            dict(name="طباعة الملصقات العلمية", price=15, days=2, kind="scientific",
                 summary="طباعة ملصقات علمية بمقاسات المؤتمرات وألوان دقيقة."),
            dict(name="طباعة الشهادات والبطاقات", price=3, days=1, kind="certificate", unit="/ قطعة",
                 summary="طباعة شهادات وبطاقات على ورق فاخر جاهز للقص والتوزيع."),
            dict(name="تجهيز ملفات المشاريع الجامعية", price=15, days=2, kind="doc",
                 summary="تجميع وتجليد وتجهيز ملفات المشاريع بالشكل المطلوب للتسليم."),
            dict(name="تصميم وطباعة اللوحات التعريفية", price=60, days=3, kind="board",
                 summary="لوحات تعريفية للمكاتب والأقسام والأنشطة بمقاسات مخصصة."),
            dict(name="تجهيز المطبوعات الخاصة بالفعاليات", price=50, days=3, kind="print",
                 summary="حزمة مطبوعات الفعالية: لافتات، بطاقات، شهادات وجداول."),
        ],
    },
    {
        "name": "خدمات المؤسسات وأعضاء هيئة التدريس",
        "slug": "faculty",
        "icon": "building",
        "description": "حلول بصرية للمحاضرات والأبحاث والمؤتمرات والمناسبات الرسمية للجهات الأكاديمية.",
        "services": [
            dict(name="تصميم العروض والمحاضرات العلمية", price=40, days=3, kind="slide",
                 summary="عروض محاضرات علمية منظمة بالمخططات والجداول والمراجع."),
            dict(name="إعداد القوالب التعليمية", price=50, days=3, kind="slide",
                 summary="قوالب تعليمية موحّدة للمقررات والبرامج الأكاديمية."),
            dict(name="تصميم الإعلانات الرسمية", price=25, days=2, kind="poster",
                 summary="إعلانات رسمية للجهات الأكاديمية بهوية موثوقة ورصينة."),
            dict(name="تصميم التقارير والملفات التعريفية", price=40, days=3, kind="doc",
                 summary="تقارير وملفات تعريفية منسقة وجاهزة للاعتماد والعرض."),
            dict(name="تجهيز المواد البصرية للمؤتمرات والندوات", price=80, days=4, kind="board",
                 summary="حزمة بصرية متكاملة للمؤتمر: شاشات، لافتات، شهادات ودعوات."),
        ],
    },
]

GALLERY = [
    ("شهادة شكر وتقدير", "certificate", "navy", "شهادات"),
    ("دعوة ندوة علمية", "invitation", "emerald", "دعوات"),
    ("عرض تقديمي أكاديمي", "slide", "royal", "عروض"),
    ("غلاف بحث جامعي", "cover", "burgundy", "أغلفة"),
    ("سيرة ذاتية احترافية", "cv", "sand", "سير ذاتية"),
    ("إعلان فعالية طلابية", "poster", "plum", "أنشطة"),
    ("هوية بصرية لركن طلابي", "logo", "navy", "هويات"),
    ("ملصق علمي لمؤتمر", "scientific", "teal", "ملصقات"),
    ("بطاقة تعريف مشارك", "card", "emerald", "بطاقات"),
]

FAQS = [
    ("كم تستغرق مدة تنفيذ الطلب؟",
     "تختلف حسب نوع الخدمة: الملفات البسيطة من نفس اليوم إلى 24 ساعة، التصاميم المتوسطة من 1 إلى 3 أيام، والهويات والمشاريع الكبيرة من 3 إلى 7 أيام. تظهر المدة المتوقعة بجانب كل خدمة."),
    ("هل يمكنني تعديل الطلب بعد إرساله؟",
     "نعم، تواصل معنا عبر واتساب برقم الطلب خلال 24 ساعة من الإرسال، وسنجري التعديلات المطلوبة قبل بدء التنفيذ."),
    ("كم عدد التعديلات المسموح بها؟",
     "كل تصميم يشمل جولتي تعديل مجانيتين، وأي تعديلات إضافية تكون برسوم رمزية يتم الاتفاق عليها مسبقاً."),
    ("كيف أستلم التصميم النهائي؟",
     "يُسلَّم التصميم عبر واتساب أو البريد الإلكتروني بصيغ عالية الجودة (PDF / PNG / JPG)، مع ملفات المصدر عند الحاجة. أما مطبوعات الطباعة فتستلمها من داخل المركز."),
    ("ما الملفات التي يجب تجهيزها قبل الطلب؟",
     "اسم الجهة أو النشاط، الشعار إن وجد، النصوص المطلوبة، الصور، ومقاس أو غرض الاستخدام. يمكنك رفع الملفات مباشرة مع نموذج الطلب."),
    ("ما طرق الدفع المتاحة؟",
     "الدفع نقداً داخل المركز أو عبر تحويل محلي، ويتم تأكيد الدفع قبل تسليم الملفات النهائية أو عند استلام المطبوعات."),
    ("هل يمكنني طلب طباعة فقط دون تصميم؟",
     "نعم، خدمات الطباعة متوفرة بشكل مستقل، ويمكنك إرسال ملفك الجاهز للطباعة مباشرة."),
    ("هل تنفذون طلبات من خارج جامعة القمة؟",
     "نعم، نخدم الجامعة والجهات والمؤسسات والأنشطة، ويمكن تنفيذ الطلبات عن بُعد مع التسليم إلكترونياً."),
]

PACKAGES = [
    dict(name="باقة الطالب", price=25, tagline="كل أدوات المذاكرة في حزمة واحدة",
         features="تنسيق بحث حتى 20 صفحة\nملخص دراسي منسق\nخريطة ذهنية واحدة\nتعديلان مجانيان",
         featured=0),
    dict(name="باقة النشاط الجامعي", price=60, tagline="تغطية بصرية كاملة لفعاليتك",
         features="إعلان فعالية بمقاسين\nدعوة إلكترونية\nشهادة مشاركة\nجدول برنامج الفعالية\nتعديلان مجانيان",
         featured=1),
    dict(name="باقة الهوية النشاطية", price=120, tagline="انطلاقة بصرية متكاملة لنشاطك",
         features="شعار احترافي\nغلاف صفحة\n3 منشورات\nقالب شهادة قابل للتعديل\nتعديلان مجانيان",
         featured=0),
]

SETTINGS = {
    "site_name": "QIMMA HUB",
    "site_name_ar": "مركز القمة للخدمات الجامعية",
    "tagline": "كل خدماتك الجامعية في مكان واحد",
    "hero_title": "كل خدماتك الجامعية في مكان واحد",
    "hero_sub": "تصميم، تنسيق، طباعة، شهادات وأنشطة جامعية — بجودة عالية وسرعة تنفيذ وأسعار مناسبة داخل جامعة القمة.",
    "about_text": "مركز القمة للخدمات الجامعية (QIMMA HUB) منصة متكاملة داخل جامعة القمة تقدم خدمات التصميم والتنسيق والطباعة والتجهيز للطلبة وأعضاء هيئة التدريس والأنشطة الجامعية. نؤمن أن جودة العمل الجامعي تبدأ من تفاصيله الصغيرة، لذلك نجمع التصميم الاحترافي والتنفيذ السريع تحت سقف واحد.",
    "whatsapp": "218940737010",
    "phone": "+218 940737010",
    "email": "qimma.hub@uni.edu.ly",
    "facebook": "https://facebook.com/qimma.hub",
    "instagram": "https://instagram.com/qimma.hub",
    "address": "داخل جامعة القمة — مبنى مركز الخدمات الجامعية",
    "hours": "السبت – الخميس: 9:00 صباحاً – 3:00 مساءً",
    "site_url": "http://127.0.0.1:8000",
    "currency": "د.ل",
    "password_changed": "0",
}

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _slugify(name, index):
    return f"s{index}"


def seed():
    db.init_db()
    if db.get_setting("seed_version") == SEED_VERSION:
        return False

    now = datetime.now().isoformat(timespec="seconds")
    styles = STYLES
    s_index = 0
    for c_index, cat in enumerate(CATEGORIES):
        cat_id = db.insert_ignore(
            "INSERT OR IGNORE INTO categories(name, slug, description, icon, sort) VALUES(?,?,?,?,?)",
            (cat["name"], cat["slug"], cat["description"], cat["icon"], c_index),
        )
        if not cat_id:
            existing = db.row("SELECT id FROM categories WHERE slug = ?", (cat["slug"],))
            cat_id = existing["id"]
        for sv_index, sv in enumerate(cat["services"]):
            s_index += 1
            service_id = db.insert_ignore(
                "INSERT OR IGNORE INTO services(category_id, name, slug, summary, description, price, price_note, unit, delivery_days, is_active, featured, sort) "
                "VALUES(?,?,?,?,?,?,?,?,?,1,?,?)",
                (cat_id, sv["name"], f"service-{s_index}", sv["summary"], sv.get("description", sv["summary"]), sv["price"],
                 "يبدأ من", sv.get("unit", ""), sv["days"], sv.get("featured", 0), sv_index),
            )
            if not service_id:
                continue
            for t_index in range(3):
                style_name, palette = styles[(s_index + t_index) % len(styles)]
                db.execute(
                    "INSERT INTO templates(service_id, title, kind, palette, sort) VALUES(?,?,?,?,?)",
                    (service_id, f"قالب {style_name}", sv["kind"], palette, t_index),
                )

    for g_index, (title, kind, palette, category) in enumerate(GALLERY):
        db.execute(
            "INSERT INTO gallery(title, kind, palette, category, sort) VALUES(?,?,?,?,?)",
            (title, kind, palette, category, g_index),
        )

    for f_index, (q, a) in enumerate(FAQS):
        db.execute("INSERT INTO faqs(question, answer, sort) VALUES(?,?,?)", (q, a, f_index))

    for p_index, p in enumerate(PACKAGES):
        db.execute(
            "INSERT INTO packages(name, tagline, price, features, featured, sort) VALUES(?,?,?,?,?,?)",
            (p["name"], p["tagline"], p["price"], p["features"], p["featured"], p_index),
        )

    for key, value in SETTINGS.items():
        db.set_setting(key, value)

    if db.scalar("SELECT COUNT(*) FROM admins", default=0) == 0:
        db.execute(
            "INSERT INTO admins(username, password_hash, created_at) VALUES(?,?,?)",
            (DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASSWORD), now),
        )

    db.set_setting("seed_version", SEED_VERSION)
    return True


if __name__ == "__main__":
    created = seed()
    print("seeded" if created else "already seeded")
