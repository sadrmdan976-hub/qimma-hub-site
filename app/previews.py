"""Render branded SVG previews for design templates and gallery items."""
import hashlib
from xml.sax.saxutils import escape

PALETTES = {
    "navy": dict(bg="#0A1D35", bg2="#143A63", accent="#C99B4E", text="#F6F1E4", sub="#A9B9CB", light=False),
    "royal": dict(bg="#12294D", bg2="#1E4478", accent="#E3C27F", text="#F4F7FC", sub="#AEBED8", light=False),
    "emerald": dict(bg="#0C3B33", bg2="#15594A", accent="#D9B36B", text="#F2F7F4", sub="#A9C4BA", light=False),
    "burgundy": dict(bg="#3A1422", bg2="#5D2135", accent="#E0BC7A", text="#FBF3F0", sub="#D0B4BC", light=False),
    "plum": dict(bg="#2B1634", bg2="#452150", accent="#E3BE7E", text="#F8F1FA", sub="#C3ADC9", light=False),
    "teal": dict(bg="#0B3038", bg2="#145060", accent="#E8C88D", text="#F2F8F9", sub="#A6C3CA", light=False),
    "sand": dict(bg="#F8F1E4", bg2="#EFE2CB", accent="#A97C36", text="#1B2A3F", sub="#6A6353", light=True),
}

FONT = "Cairo, Tajawal, Segoe UI, Tahoma, sans-serif"


def fit(text, max_width, base, minimum=16):
    if not text:
        return base
    size = int(max_width / (max(len(text), 1) * 0.56))
    return max(minimum, min(base, size))


def _defs(p, w, h):
    return f"""
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{p['bg']}"/><stop offset="1" stop-color="{p['bg2']}"/>
 </linearGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{p['accent']}" stop-opacity=".55"/>
  <stop offset=".5" stop-color="{p['accent']}"/>
  <stop offset="1" stop-color="{p['accent']}" stop-opacity=".55"/>
 </linearGradient>
</defs>"""


def _base(p, w, h, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{FONT}">{_defs(p, w, h)}
<rect width="{w}" height="{h}" fill="url(#bg)"/>""" + body + "</svg>"


def _dots(p, x, y, cols=4, rows=3, gap=18, r=2.2, opacity=0.35):
    out = []
    for i in range(cols):
        for j in range(rows):
            out.append(f'<circle cx="{x + i * gap}" cy="{y + j * gap}" r="{r}" fill="{p["accent"]}" opacity="{opacity}"/>')
    return "".join(out)


def _mark(p, cx, cy, r, accent=None):
    accent = accent or p["accent"]
    return f"""<g>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{accent}" stroke-width="{max(2, r * 0.06)}"/>
<path d="M {cx - r * 0.62} {cy + r * 0.08} L {cx - r * 0.22} {cy - r * 0.5} L {cx + r * 0.02} {cy - r * 0.12} L {cx + r * 0.28} {cy - r * 0.58} L {cx + r * 0.62} {cy + r * 0.08}" fill="none" stroke="{accent}" stroke-width="{max(2, r * 0.09)}" stroke-linejoin="round"/>
<path d="M {cx - r * 0.55} {cy + r * 0.42} Q {cx} {cy + r * 0.16} {cx + r * 0.55} {cy + r * 0.42}" fill="none" stroke="{p['text']}" stroke-width="{max(1.6, r * 0.05)}" stroke-linecap="round"/>
<path d="M {cx - r * 0.55} {cy + r * 0.5} Q {cx} {cy + r * 0.26} {cx + r * 0.55} {cy + r * 0.5}" fill="none" stroke="{p['text']}" stroke-width="{max(1.6, r * 0.05)}" stroke-linecap="round"/>
</g>"""


def _frame(p, w, h, inset=26, sw=2):
    return (f'<rect x="{inset}" y="{inset}" width="{w - inset * 2}" height="{h - inset * 2}" rx="10" '
            f'fill="none" stroke="{p["accent"]}" stroke-opacity=".75" stroke-width="{sw}"/>'
            f'<rect x="{inset + 10}" y="{inset + 10}" width="{w - inset * 2 - 20}" height="{h - inset * 2 - 20}" rx="6" '
            f'fill="none" stroke="{p["accent"]}" stroke-opacity=".28" stroke-width="1"/>')


def _title(p, text, x, y, width, base, anchor="middle", weight="700", fill=None, minimum=16):
    fs = fit(text, width, base, minimum)
    fill = fill or p["text"]
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" font-weight="{weight}" '
            f'fill="{fill}">{escape(text)}</text>')


def _lines(p, x, y, width, count, gap=26, heights=None, opacity=0.32, anchor="start"):
    out = []
    for i in range(count):
        w = width if not heights else width * heights[i % len(heights)]
        y2 = y + i * gap
        x2 = x if anchor == "start" else x - w
        out.append(f'<rect x="{x2:.0f}" y="{y2}" width="{w:.0f}" height="7" rx="3.5" fill="{p["text"]}" opacity="{opacity}"/>')
    return "".join(out)


def _logo_corner(p, w, h, size=56, margin=34):
    return _mark(p, w - margin - size / 2, margin + size / 2, size / 2)


# ---------------------------------------------------------------- kinds

def certificate(p, title):
    w, h = 1160, 820
    body = f"""
{_frame(p, w, h, 24, 3)}
{_frame(p, w, h, 40, 1)}
{_dots(p, 58, 52, 3, 2, 16, 2.5, 0.5)}
{_dots(p, w - 100, h - 88, 3, 2, 16, 2.5, 0.5)}
{_mark(p, w / 2, 118, 38)}
<text x="{w / 2}" y="196" text-anchor="middle" font-size="22" fill="{p['sub']}" letter-spacing="6">CERTIFICATE</text>
{_title(p, title or 'شهادة شكر وتقدير', w / 2, 268, 860, 52, weight='800')}
<rect x="{w / 2 - 70}" y="300" width="140" height="3" rx="1.5" fill="{p['accent']}"/>
<text x="{w / 2}" y="366" text-anchor="middle" font-size="24" fill="{p['sub']}">تُمنح هذه الشهادة إلى</text>
<text x="{w / 2}" y="452" text-anchor="middle" font-size="40" font-weight="700" fill="{p['accent']}">الاسم الكريم</text>
<rect x="{w / 2 - 190}" y="476" width="380" height="1.5" fill="{p['accent']}" opacity=".6"/>
{_lines(p, w / 2 - 280, 522, 560, 2, 30, [1, .86], 0.28, 'start')}
<circle cx="190" cy="676" r="64" fill="none" stroke="{p['accent']}" stroke-opacity=".8" stroke-width="2"/>
<circle cx="190" cy="676" r="50" fill="none" stroke="{p['accent']}" stroke-opacity=".4" stroke-width="1"/>
<text x="190" y="668" text-anchor="middle" font-size="16" fill="{p['accent']}">ختم</text>
<text x="190" y="692" text-anchor="middle" font-size="16" fill="{p['accent']}">المركز</text>
<rect x="118" y="762" width="144" height="1.5" fill="{p['sub']}" opacity=".5"/>
<text x="190" y="790" text-anchor="middle" font-size="18" fill="{p['sub']}">التوقيع</text>
<rect x="{w - 262}" y="762" width="144" height="1.5" fill="{p['sub']}" opacity=".5"/>
<text x="{w - 190}" y="790" text-anchor="middle" font-size="18" fill="{p['sub']}">المدير</text>
"""
    return _base(p, w, h, body)


def invitation(p, title):
    w, h = 800, 1060
    body = f"""
<rect x="46" y="46" width="{w - 92}" height="{h - 92}" rx="230" fill="none" stroke="{p['accent']}" stroke-width="2" stroke-opacity=".8"/>
<rect x="62" y="62" width="{w - 124}" height="{h - 124}" rx="216" fill="none" stroke="{p['accent']}" stroke-width="1" stroke-opacity=".3"/>
{_mark(p, w / 2, 190, 44)}
<text x="{w / 2}" y="286" text-anchor="middle" font-size="30" fill="{p['accent']}" letter-spacing="3">دعوة</text>
{_title(p, title or 'دعوة ندوة علمية', w / 2, 366, 600, 46, weight='800')}
<rect x="{w / 2 - 54}" y="394" width="108" height="2.5" fill="{p['accent']}"/>
{_lines(p, w / 2 - 210, 462, 420, 3, 34, [1, .78, .9], 0.3, 'start')}
<circle cx="{w / 2}" cy="700" r="86" fill="none" stroke="{p['accent']}" stroke-opacity=".55" stroke-width="1.5"/>
<text x="{w / 2}" y="682" text-anchor="middle" font-size="20" fill="{p['sub']}">الموعد</text>
<text x="{w / 2}" y="722" text-anchor="middle" font-size="30" font-weight="700" fill="{p['accent']}">00 : 00</text>
<rect x="{w / 2 - 190}" y="846" width="380" height="74" rx="37" fill="{p['accent']}" opacity=".14"/>
<text x="{w / 2}" y="892" text-anchor="middle" font-size="21" fill="{p['text']}">القاعة الرئيسية — جامعة القمة</text>
{_dots(p, 86, 952, 5, 2, 16, 2.5, 0.45)}
{_dots(p, w - 152, 952, 2, 2, 16, 2.5, 0.45)}
"""
    return _base(p, w, h, body)


def cover(p, title):
    w, h = 800, 1060
    body = f"""
<path d="M0 0 H{w} V330 C 600 380, 420 260, 250 330 C 150 372, 60 350, 0 318 Z" fill="{p['accent']}" opacity=".13"/>
<path d="M0 1060 V820 L 230 700 L 360 790 L 560 640 L 800 760 V1060 Z" fill="{p['accent']}" opacity=".16"/>
<circle cx="640" cy="170" r="96" fill="none" stroke="{p['accent']}" stroke-opacity=".35" stroke-width="1.5"/>
<circle cx="640" cy="170" r="70" fill="none" stroke="{p['accent']}" stroke-opacity=".22" stroke-width="1"/>
{_mark(p, 96, 96, 34)}
<text x="150" y="106" font-size="22" font-weight="700" fill="{p['text']}">QIMMA HUB</text>
<text x="150" y="128" font-size="13" fill="{p['sub']}" letter-spacing="1">UNIVERSITY SERVICES CENTER</text>
{_title(p, title or 'غلاف بحث جامعي', w / 2, 500, 600, 48, weight='800')}
<rect x="{w / 2 - 60}" y="536" width="120" height="3" fill="{p['accent']}"/>
{_lines(p, w / 2 - 170, 596, 340, 2, 30, [1, .7], 0.3, 'start')}
<rect x="86" y="920" width="628" height="1.5" fill="{p['accent']}" opacity=".5"/>
<text x="86" y="962" font-size="19" fill="{p['sub']}">إعداد: ........................</text>
<text x="{w - 86}" y="962" text-anchor="end" font-size="19" fill="{p['sub']}">إشراف: ........................</text>
"""
    return _base(p, w, h, body)


def doc(p, title):
    w, h = 800, 1060
    ink = p["text"]
    body = f"""
<rect x="46" y="56" width="{w - 92}" height="{h - 112}" rx="14" fill="{ink}" opacity="{0.96 if p['light'] else 0.07}"/>
<rect x="46" y="56" width="{w - 92}" height="10" rx="5" fill="{p['accent']}"/>
{_mark(p, w - 92, 106, 20)}
{_title(p, title or 'ملخص منسق', w / 2, 200, 560, 40, weight='800')}
<rect x="{w / 2 - 60}" y="228" width="120" height="2.5" fill="{p['accent']}"/>
{_lines(p, 110, 300, 580, 9, 34, [1, .92, .97, .7, .95, .88, .99, .62, .9], 0.26, 'start')}
<rect x="110" y="648" width="{w - 220}" height="120" rx="10" fill="{p['accent']}" opacity=".12"/>
<rect x="132" y="674" width="220" height="8" rx="4" fill="{p['accent']}" opacity=".65"/>
{_lines(p, 132, 700, 240, 2, 24, [1, .8], 0.3, 'start')}
{_lines(p, 110, 820, 580, 4, 34, [.98, .9, .96, .55], 0.26, 'start')}
<rect x="110" y="978" width="140" height="6" rx="3" fill="{p['accent']}" opacity=".5"/>
<text x="{w - 110}" y="990" text-anchor="end" font-size="15" fill="{p['sub']}">QIMMA HUB</text>
"""
    return _base(p, w, h, body)


def slide(p, title):
    w, h = 1200, 700
    body = f"""
<rect x="0" y="0" width="10" height="{h}" fill="{p['accent']}"/>
{_mark(p, 78, 74, 26)}
<text x="124" y="70" font-size="18" font-weight="700" fill="{p['text']}">QIMMA HUB</text>
<text x="124" y="92" font-size="12" fill="{p['sub']}" letter-spacing="1">PRESENTATION</text>
{_title(p, title or 'عرض تقديمي', 74, 214, 640, 46, anchor='start', weight='800')}
<rect x="76" y="248" width="110" height="3" fill="{p['accent']}"/>
{_lines(p, 76, 306, 560, 5, 42, [.95, .75, .88, .62, .8], 0.3, 'start')}
<circle cx="86" cy="309" r="4" fill="{p['accent']}"/><circle cx="86" cy="351" r="4" fill="{p['accent']}"/>
<circle cx="86" cy="393" r="4" fill="{p['accent']}"/><circle cx="86" cy="435" r="4" fill="{p['accent']}"/>
<circle cx="86" cy="477" r="4" fill="{p['accent']}"/>
<rect x="730" y="180" width="392" height="356" rx="18" fill="{p['text']}" opacity=".06"/>
<rect x="730" y="180" width="392" height="356" rx="18" fill="none" stroke="{p['accent']}" stroke-opacity=".22"/>
<g fill="{p['accent']}">
 <rect x="782" y="402" width="38" height="94" rx="6" opacity=".55"/>
 <rect x="840" y="356" width="38" height="140" rx="6" opacity=".7"/>
 <rect x="898" y="310" width="38" height="186" rx="6" opacity=".85"/>
 <rect x="956" y="270" width="38" height="226" rx="6"/>
 <rect x="1014" y="330" width="38" height="166" rx="6" opacity=".7"/>
</g>
<rect x="782" y="520" width="270" height="1.5" fill="{p['sub']}" opacity=".3"/>
<text x="782" y="238" font-size="18" fill="{p['sub']}">نظرة عامة</text>
<rect x="76" y="606" width="1048" height="1" fill="{p['accent']}" opacity=".25"/>
<text x="76" y="646" font-size="15" fill="{p['sub']}">مركز القمة للخدمات الجامعية</text>
<text x="{w - 76}" y="646" text-anchor="end" font-size="15" fill="{p['sub']}">01</text>
"""
    return _base(p, w, h, body)


def map(p, title):
    w, h = 900, 900
    cx, cy = w / 2, h / 2
    nodes = [(cx - 300, cy - 240), (cx + 300, cy - 240), (cx - 330, cy + 60),
             (cx + 330, cy + 60), (cx - 190, cy + 290), (cx + 190, cy + 290)]
    body = [f'<rect x="40" y="40" width="{w - 80}" height="{h - 80}" rx="24" fill="none" stroke="{p["accent"]}" stroke-opacity=".22"/>']
    for x, y in nodes:
        body.append(f'<path d="M {cx} {cy} L {x} {y}" stroke="{p["accent"]}" stroke-opacity=".4" stroke-width="1.6"/>')
    for i, (x, y) in enumerate(nodes):
        body.append(f'<circle cx="{x}" cy="{y}" r="46" fill="{p["accent"]}" opacity=".14"/>')
        body.append(f'<circle cx="{x}" cy="{y}" r="46" fill="none" stroke="{p["accent"]}" stroke-opacity=".6"/>')
        body.append(f'<text x="{x}" y="{y + 7}" text-anchor="middle" font-size="20" fill="{p["accent"]}" font-weight="700">{i + 1}</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="92" fill="{p["accent"]}" opacity=".16"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="{p["accent"]}" stroke-width="2"/>')
    body.append(_title(p, title or 'خريطة ذهنية', cx, cy + 8, 150, 24, weight='800'))
    body.append(_title(p, 'الموضوع الرئيسي', cx, cy + 40, 140, 13, weight='400', fill=p['sub']))
    body.append(f'<text x="{cx}" y="{h - 66}" text-anchor="middle" font-size="14" fill="{p["sub"]}">QIMMA HUB</text>')
    return _base(p, w, h, "".join(body))


def cv(p, title):
    w, h = 800, 1060
    body = f"""
<rect x="0" y="0" width="270" height="{h}" fill="{p['text']}" opacity="{0.06 if not p['light'] else 0.05}"/>
<rect x="0" y="0" width="270" height="6" fill="{p['accent']}"/>
{_mark(p, 135, 170, 62)}
<circle cx="135" cy="170" r="86" fill="none" stroke="{p['accent']}" stroke-opacity=".3"/>
<text x="135" y="310" text-anchor="middle" font-size="27" font-weight="800" fill="{p['text']}">الاسم الكامل</text>
<text x="135" y="344" text-anchor="middle" font-size="16" fill="{p['sub']}">المسمى الوظيفي</text>
<rect x="60" y="390" width="150" height="2" fill="{p['accent']}" opacity=".6"/>
<text x="40" y="452" font-size="17" font-weight="700" fill="{p['accent']}">التواصل</text>
{_lines(p, 40, 480, 190, 5, 30, [.9, .75, .85, .8, .6], 0.28, 'start')}
<text x="40" y="690" font-size="17" font-weight="700" fill="{p['accent']}">المهارات</text>
{_lines(p, 40, 718, 190, 4, 30, [.9, .8, .85, .65], 0.28, 'start')}
<text x="320" y="118" font-size="38" font-weight="800" fill="{p['text']}">السيرة الذاتية</text>
<rect x="320" y="140" width="110" height="3" fill="{p['accent']}"/>
<text x="320" y="206" font-size="19" font-weight="700" fill="{p['accent']}">نبذة</text>
{_lines(p, 320, 230, 400, 3, 28, [1, .94, .8], 0.26, 'start')}
<text x="320" y="348" font-size="19" font-weight="700" fill="{p['accent']}">الخبرات</text>
{_lines(p, 320, 372, 400, 4, 28, [.95, .88, .9, .7], 0.26, 'start')}
<text x="320" y="514" font-size="19" font-weight="700" fill="{p['accent']}">التعليم</text>
{_lines(p, 320, 538, 400, 3, 28, [.92, .85, .6], 0.26, 'start')}
<text x="320" y="656" font-size="19" font-weight="700" fill="{p['accent']}">اللغات</text>
{_lines(p, 320, 680, 400, 2, 28, [.8, .65], 0.26, 'start')}
<rect x="320" y="770" width="400" height="170" rx="12" fill="{p['accent']}" opacity=".1"/>
<text x="344" y="812" font-size="16" fill="{p['sub']}">QIMMA HUB — سيرة ذاتية احترافية</text>
{_lines(p, 344, 834, 340, 3, 26, [1, .9, .6], 0.25, 'start')}
"""
    return _base(p, w, h, body)


def poster(p, title):
    w, h = 800, 1000
    body = f"""
<path d="M0 0 H{w} V210 C 630 300, 470 150, 330 230 C 210 300, 90 250, 0 210 Z" fill="{p['accent']}" opacity=".16"/>
<path d="M0 1000 V760 L 210 640 L 360 730 L 540 580 L 800 720 V1000 Z" fill="{p['accent']}" opacity=".13"/>
{_dots(p, 58, 58, 4, 3, 20, 2.5, 0.5)}
{_mark(p, 92, 92, 30)}
<text x="138" y="86" font-size="19" font-weight="700" fill="{p['text']}">QIMMA HUB</text>
<text x="138" y="108" font-size="11" fill="{p['sub']}" letter-spacing="1">UNIVERSITY SERVICES</text>
<rect x="70" y="292" width="94" height="30" rx="15" fill="{p['accent']}" opacity=".85"/>
<text x="117" y="313" text-anchor="middle" font-size="14" font-weight="700" fill="{p['bg']}">فعالية</text>
{_title(p, title or 'إعلان فعالية', 70, 418, 660, 60, anchor='start', weight='800')}
<rect x="72" y="452" width="130" height="4" fill="{p['accent']}"/>
{_lines(p, 72, 508, 480, 2, 30, [.95, .72], 0.3, 'start')}
<rect x="70" y="806" width="660" height="104" rx="16" fill="{p['accent']}" opacity=".12"/>
<rect x="70" y="806" width="660" height="104" rx="16" fill="none" stroke="{p['accent']}" stroke-opacity=".4"/>
<text x="104" y="850" font-size="15" fill="{p['sub']}">احفظ التاريخ</text>
<text x="104" y="886" font-size="28" font-weight="800" fill="{p['accent']}">00 / 00 / 2026</text>
<rect x="556" y="838" width="140" height="42" rx="21" fill="{p['accent']}"/>
<text x="626" y="866" text-anchor="middle" font-size="15" font-weight="700" fill="{p['bg']}">سجّل الآن</text>
<text x="70" y="962" font-size="14" fill="{p['sub']}">جامعة القمة — القاعة الرئيسية</text>
"""
    return _base(p, w, h, body)


def card(p, title):
    w, h = 1200, 700
    body = f"""
{_dots(p, 84, 120, 4, 3, 20, 2.4, 0.35)}
{_dots(p, w - 168, h - 190, 4, 3, 20, 2.4, 0.35)}
<rect x="250" y="120" width="700" height="460" rx="26" fill="{p['text']}" opacity="{0.05 if not p['light'] else 0.04}"/>
<rect x="250" y="120" width="700" height="460" rx="26" fill="none" stroke="{p['accent']}" stroke-opacity=".6" stroke-width="2"/>
<rect x="250" y="120" width="700" height="14" rx="7" fill="{p['accent']}"/>
<rect x="500" y="96" width="200" height="14" rx="7" fill="{p['accent']}" opacity=".5"/>
{_mark(p, 600, 74, 22)}
<circle cx="380" cy="330" r="74" fill="{p['accent']}" opacity=".16"/>
<circle cx="380" cy="330" r="74" fill="none" stroke="{p['accent']}" stroke-opacity=".6"/>
<circle cx="380" cy="305" r="26" fill="{p['accent']}" opacity=".55"/>
<path d="M 336 372 Q 380 332 424 372 L 424 398 L 336 398 Z" fill="{p['accent']}" opacity=".55"/>
<text x="490" y="276" font-size="17" fill="{p['sub']}">بطاقة مشارك</text>
{_title(p, title or 'مشارك', 490, 336, 340, 38, anchor='start', weight='800')}
<rect x="490" y="360" width="120" height="2.5" fill="{p['accent']}"/>
{_lines(p, 490, 404, 300, 3, 30, [.85, .7, .6], 0.28, 'start')}
<rect x="820" y="300" width="96" height="96" rx="8" fill="{p['text']}" opacity=".12"/>
<rect x="820" y="300" width="96" height="96" rx="8" fill="none" stroke="{p['accent']}" stroke-opacity=".45"/>
<rect x="834" y="314" width="26" height="26" fill="{p['accent']}" opacity=".8"/>
<rect x="876" y="314" width="26" height="26" fill="{p['text']}" opacity=".25"/>
<rect x="834" y="356" width="26" height="26" fill="{p['text']}" opacity=".25"/>
<rect x="876" y="356" width="26" height="26" fill="{p['accent']}" opacity=".6"/>
<rect x="250" y="540" width="700" height="40" rx="0" fill="{p['accent']}" opacity=".12"/>
<text x="600" y="567" text-anchor="middle" font-size="15" fill="{p['sub']}" letter-spacing="2">QIMMA HUB · UNIVERSITY SERVICES CENTER</text>
"""
    return _base(p, w, h, body)


def schedule(p, title):
    w, h = 1200, 700
    rows = 6
    body = [
        f'<rect x="60" y="60" width="{w - 120}" height="86" rx="14" fill="{p["accent"]}" opacity=".14"/>',
        f'<rect x="60" y="60" width="{w - 120}" height="86" rx="14" fill="none" stroke="{p["accent"]}" stroke-opacity=".4"/>',
        _mark(p, 116, 103, 26),
        _title(p, title or 'جدول الفعاليات', 170, 104, 640, 34, anchor='start', weight='800'),
        f'<text x="{w - 104}" y="114" text-anchor="end" font-size="16" fill="{p["sub"]}">PROGRAM</text>',
    ]
    top = 182
    row_h = 70
    for i in range(rows):
        y = top + i * row_h
        if i % 2 == 0:
            body.append(f'<rect x="60" y="{y}" width="{w - 120}" height="{row_h}" fill="{p["text"]}" opacity=".04"/>')
        body.append(f'<rect x="60" y="{y}" width="150" height="{row_h}" fill="{p["accent"]}" opacity=".13"/>')
        body.append(f'<text x="135" y="{y + 44}" text-anchor="middle" font-size="21" font-weight="700" fill="{p["accent"]}">00:00</text>')
        body.append(f'<text x="250" y="{y + 34}" font-size="19" font-weight="700" fill="{p["text"]}">عنوان الفقرة {i + 1}</text>')
        body.append(f'<rect x="250" y="{y + 48}" width="{300 + (i * 60) % 220}" height="7" rx="3.5" fill="{p["text"]}" opacity=".22"/>')
        body.append(f'<line x1="60" y1="{y}" x2="{w - 60}" y2="{y}" stroke="{p["accent"]}" stroke-opacity=".16"/>')
    body.append(f'<line x1="210" y1="182" x2="210" y2="{top + rows * row_h}" stroke="{p["accent"]}" stroke-opacity=".3"/>')
    body.append(f'<rect x="60" y="{top + rows * row_h}" width="{w - 120}" height="1.5" fill="{p["accent"]}" opacity=".4"/>')
    return _base(p, w, h, "".join(body))


def logo(p, title):
    w = h = 900
    body = f"""
{_dots(p, 90, 90, 6, 4, 26, 2.4, 0.3)}
{_dots(p, w - 220, h - 230, 5, 4, 26, 2.4, 0.3)}
<circle cx="{w / 2}" cy="420" r="230" fill="none" stroke="{p['accent']}" stroke-opacity=".25"/>
<circle cx="{w / 2}" cy="420" r="196" fill="none" stroke="{p['accent']}" stroke-opacity=".45" stroke-width="2"/>
{_mark(p, w / 2, 420, 168)}
{_title(p, title or 'شعار وهوية', w / 2, 700, 640, 40, weight='800')}
<text x="{w / 2}" y="742" text-anchor="middle" font-size="18" fill="{p['sub']}" letter-spacing="4">BRAND IDENTITY</text>
<rect x="{w / 2 - 66}" y="775" width="132" height="2.5" fill="{p['accent']}"/>
<text x="{w / 2}" y="828" text-anchor="middle" font-size="15" fill="{p['sub']}">QIMMA HUB — مركز القمة للخدمات الجامعية</text>
"""
    return _base(p, w, h, body)


def video(p, title):
    w, h = 1200, 675
    body = f"""
<rect x="0" y="0" width="{w}" height="54" fill="#000" opacity=".28"/>
<rect x="0" y="{h - 54}" width="{w}" height="54" fill="#000" opacity=".28"/>
{''.join(f'<rect x="{40 + i * 76}" y="18" width="40" height="18" rx="4" fill="{p["text"]}" opacity=".25"/>' for i in range(15))}
{''.join(f'<rect x="{40 + i * 76}" y="{h - 36}" width="40" height="18" rx="4" fill="{p["text"]}" opacity=".25"/>' for i in range(15))}
<circle cx="{w / 2}" cy="{h / 2 - 20}" r="86" fill="{p['accent']}" opacity=".92"/>
<path d="M {w / 2 - 24} {h / 2 - 62} L {w / 2 + 46} {h / 2 - 20} L {w / 2 - 24} {h / 2 + 22} Z" fill="{p['bg']}"/>
{_title(p, title or 'فيديو ترويجي', 80, 560, 640, 38, anchor='start', weight='800')}
<rect x="80" y="584" width="{w - 280}" height="3" rx="1.5" fill="{p['accent']}" opacity=".35"/>
<rect x="80" y="584" width="290" height="3" rx="1.5" fill="{p['accent']}"/>
<text x="{w - 80}" y="596" text-anchor="end" font-size="15" fill="{p['sub']}">00:45</text>
<text x="80" y="120" font-size="14" fill="{p['sub']}" letter-spacing="3">QIMMA HUB · PROMO</text>
"""
    return _base(p, w, h, body)


def qr(p, title):
    w = h = 800
    seed = int(hashlib.sha256((title or "qr").encode()).hexdigest(), 16)
    cells = 21
    cell = 22
    origin = (w - cells * cell) / 2
    out = [f'<rect x="90" y="90" width="{w - 180}" height="{h - 180}" rx="30" fill="{p["text"]}" opacity="{0.06}"/>',
           f'<rect x="90" y="90" width="{w - 180}" height="{h - 180}" rx="30" fill="none" stroke="{p["accent"]}" stroke-opacity=".5" stroke-width="2"/>']
    out.append(f'<rect x="{origin - 22}" y="{origin - 22}" width="{cells * cell + 44}" height="{cells * cell + 44}" rx="18" fill="#FFFFFF"/>')
    state = seed
    for i in range(cells):
        for j in range(cells):
            if (i < 7 and j < 7) or (i < 7 and j > 13) or (i > 13 and j < 7):
                continue
            state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
            if (state >> 33) & 1:
                out.append(f'<rect x="{origin + j * cell}" y="{origin + i * cell}" width="{cell - 2}" height="{cell - 2}" fill="#0A1D35"/>')
    for ox, oy in [(0, 0), (cells - 7, 0), (0, cells - 7)]:
        x = origin + ox * cell
        y = origin + oy * cell
        out.append(f'<rect x="{x}" y="{y}" width="{7 * cell}" height="{7 * cell}" fill="#0A1D35"/>')
        out.append(f'<rect x="{x + cell}" y="{y + cell}" width="{5 * cell}" height="{5 * cell}" fill="#FFFFFF"/>')
        out.append(f'<rect x="{x + 2 * cell}" y="{y + 2 * cell}" width="{3 * cell}" height="{3 * cell}" fill="#0A1D35"/>')
    out.append(f'<text x="{w / 2}" y="120" text-anchor="middle" font-size="22" fill="{p["accent"]}" font-weight="700">امسح الرمز</text>')
    out.append(_title(p, title or 'رمز QR', w / 2, 742, 560, 26, weight='700'))
    return _base(p, w, h, "".join(out))


def print_(p, title):
    w = h = 900
    body = f"""
<g transform="rotate(-8 450 380)">
 <rect x="220" y="180" width="420" height="520" rx="8" fill="{p['text']}" opacity=".08"/>
</g>
<g transform="rotate(4 450 380)">
 <rect x="240" y="170" width="420" height="520" rx="8" fill="{p['text']}" opacity=".14"/>
</g>
<rect x="260" y="160" width="420" height="520" rx="8" fill="{p['text']}" opacity="{0.95 if p['light'] else 0.16}"/>
<rect x="260" y="160" width="420" height="12" rx="6" fill="{p['accent']}"/>
{_mark(p, 620, 210, 18)}
{_title(p, title or 'طباعة وتجهيز', 470, 300, 340, 30, weight='800')}
{_lines(p, 300, 344, 340, 8, 26, [1, .9, .96, .7, .92, .85, .98, .6], 0.24, 'start')}
<rect x="300" y="576" width="340" height="1.5" fill="{p['accent']}" opacity=".5"/>
<text x="300" y="612" font-size="15" fill="{p['sub']}">QIMMA HUB — جودة طباعة عالية</text>
<text x="{w / 2}" y="790" text-anchor="middle" font-size="18" fill="{p['sub']}" letter-spacing="3">PRINT &amp; FINISHING</text>
"""
    return _base(p, w, h, body)


def scientific(p, title):
    w, h = 900, 1200
    body = f"""
<rect x="40" y="40" width="{w - 80}" height="{h - 80}" rx="12" fill="{p['text']}" opacity=".05"/>
<rect x="40" y="40" width="{w - 80}" height="150" rx="12" fill="{p['accent']}" opacity=".16"/>
{_mark(p, 116, 114, 36)}
<text x="176" y="104" font-size="17" fill="{p['sub']}" letter-spacing="2">QIMMA HUB</text>
{_title(p, title or 'ملصق علمي', 176, 152, 520, 32, anchor='start', weight='800')}
<line x1="40" y1="190" x2="{w - 40}" y2="190" stroke="{p['accent']}" stroke-opacity=".4"/>
<g>
 <rect x="80" y="242" width="340" height="330" rx="10" fill="{p['accent']}" opacity=".13"/>
 <text x="104" y="284" font-size="20" font-weight="700" fill="{p['accent']}">المقدمة</text>
 {_lines(p, 104, 316, 290, 7, 28, [.98, .88, .95, .8, .92, .85, .6], 0.25, 'start')}
 <rect x="480" y="242" width="340" height="330" rx="10" fill="{p['accent']}" opacity=".07"/>
 <text x="504" y="284" font-size="20" font-weight="700" fill="{p['accent']}">المنهجية</text>
 {_lines(p, 504, 316, 290, 7, 28, [.96, .9, .84, .97, .8, .88, .55], 0.25, 'start')}
 <rect x="80" y="612" width="740" height="230" rx="10" fill="{p['accent']}" opacity=".07"/>
 <text x="104" y="654" font-size="20" font-weight="700" fill="{p['accent']}">النتائج</text>
 <g fill="{p['accent']}">
  <rect x="130" y="730" width="40" height="80" rx="5" opacity=".5"/>
  <rect x="190" y="700" width="40" height="110" rx="5" opacity=".65"/>
  <rect x="250" y="676" width="40" height="134" rx="5" opacity=".8"/>
  <rect x="310" y="712" width="40" height="98" rx="5" opacity=".6"/>
  <rect x="370" y="686" width="40" height="124" rx="5" opacity=".75"/>
 </g>
 {_lines(p, 470, 690, 320, 5, 30, [.96, .88, .9, .82, .6], 0.25, 'start')}
 <rect x="80" y="878" width="740" height="190" rx="10" fill="{p['accent']}" opacity=".07"/>
 <text x="104" y="920" font-size="20" font-weight="700" fill="{p['accent']}">الخلاصة والمراجع</text>
 {_lines(p, 104, 952, 620, 3, 30, [.96, .9, .66], 0.25, 'start')}
</g>
<text x="{w / 2}" y="1124" text-anchor="middle" font-size="15" fill="{p['sub']}">ملصق علمي — مؤتمر / ندوة</text>
"""
    return _base(p, w, h, body)


def board(p, title):
    w, h = 1200, 700
    body = f"""
<line x1="430" y1="0" x2="430" y2="96" stroke="{p['sub']}" stroke-opacity=".5" stroke-width="2"/>
<line x1="770" y1="0" x2="770" y2="96" stroke="{p['sub']}" stroke-opacity=".5" stroke-width="2"/>
<rect x="170" y="96" width="860" height="420" rx="20" fill="{p['text']}" opacity=".07"/>
<rect x="170" y="96" width="860" height="420" rx="20" fill="none" stroke="{p['accent']}" stroke-opacity=".6" stroke-width="2"/>
<rect x="170" y="96" width="860" height="10" rx="5" fill="{p['accent']}"/>
{_mark(p, 300, 306, 76)}
<text x="440" y="250" font-size="20" fill="{p['sub']}">QIMMA HUB</text>
{_title(p, title or 'لوحة تعريفية', 440, 330, 520, 44, anchor='start', weight='800')}
<rect x="440" y="358" width="130" height="3" fill="{p['accent']}"/>
{_lines(p, 440, 396, 470, 2, 28, [.9, .65], 0.26, 'start')}
<rect x="300" y="566" width="600" height="40" rx="20" fill="{p['accent']}" opacity=".16"/>
<text x="600" y="593" text-anchor="middle" font-size="17" fill="{p['sub']}">UNIVERSITY SERVICES CENTER</text>
"""
    return _base(p, w, h, body)


RENDERERS = {
    "certificate": certificate,
    "invitation": invitation,
    "cover": cover,
    "doc": doc,
    "slide": slide,
    "map": map,
    "cv": cv,
    "poster": poster,
    "card": card,
    "schedule": schedule,
    "logo": logo,
    "video": video,
    "qr": qr,
    "print": print_,
    "scientific": scientific,
    "board": board,
}

KIND_LABELS = {
    "certificate": "شهادة",
    "invitation": "دعوة",
    "cover": "غلاف",
    "doc": "مستند",
    "slide": "عرض تقديمي",
    "map": "خريطة ذهنية",
    "cv": "سيرة ذاتية",
    "poster": "منشور",
    "card": "بطاقة",
    "schedule": "جدول",
    "logo": "هوية بصرية",
    "video": "فيديو",
    "qr": "رمز QR",
    "print": "طباعة",
    "scientific": "ملصق علمي",
    "board": "لوحة",
}


def svg(kind, palette, title):
    p = PALETTES.get(palette, PALETTES["navy"])
    renderer = RENDERERS.get(kind, poster)
    return renderer(p, title)
