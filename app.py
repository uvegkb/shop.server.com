import os
import sqlite3
from datetime import datetime
from typing import Dict, List

import stripe
import smtplib
import sys
from email.message import EmailMessage
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shop.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

CURRENCY = os.environ.get("SHOP_CURRENCY", "USD")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_SENDER_NAME = os.environ.get("EMAIL_SENDER_NAME", "Aurora Store")

try:
    import config  # local-only secrets

    EMAIL_USER = getattr(config, "EMAIL_USER", EMAIL_USER)
    EMAIL_APP_PASSWORD = getattr(config, "EMAIL_APP_PASSWORD", EMAIL_APP_PASSWORD)
    EMAIL_SENDER_NAME = getattr(config, "EMAIL_SENDER_NAME", EMAIL_SENDER_NAME)
except Exception:
    pass

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
)

TEXT = {
    "en": {
        "brand": "Aurora Store",
        "tagline": "Shop your way and enjoy picks that actually fit your day",
        "cta": "Browse the collection",
        "nav_home": "Home",
        "nav_products": "Products",
        "nav_story": "Story",
        "nav_contact": "Contact",
        "featured": "Featured Drops",
        "add_to_cart": "Add to cart",
        "view": "View",
        "cart": "Cart",
        "checkout": "Checkout",
        "empty_cart": "Your cart is empty for now.",
        "subtotal": "Subtotal",
        "shipping": "Shipping",
        "total": "Total",
        "email": "Email",
        "pay_now": "Pay now",
        "success": "Payment complete",
        "cancel": "Payment canceled",
        "back": "Back to store",
        "products": "Products",
        "details": "Product details",
        "language": "العربية",
        "newsletter_title": "Stay in the loop",
        "newsletter_text": "New picks and updates, only when it matters.",
        "subscribe": "Subscribe",
        "footer_note": "Here to help — shop with comfort and confidence",
        "comments": "Comments",
        "add_comment": "Add a comment",
        "name": "Name",
        "comment": "Comment",
        "edit": "Edit",
        "delete": "Delete",
        "save": "Save",
    },
    "ar": {
        "brand": "متجر أورورا",
        "tagline": "تسوّق براحتك واستمتع باختيارات تهمّك فعلاً",
        "cta": "تسوّق الآن",
        "nav_home": "الرئيسية",
        "nav_products": "المنتجات",
        "nav_story": "قصتنا",
        "nav_contact": "تواصل",
        "featured": "مختارات مميزة",
        "add_to_cart": "أضف للسلة",
        "view": "عرض",
        "cart": "السلة",
        "checkout": "إتمام الدفع",
        "empty_cart": "السلة فاضية حالياً.",
        "subtotal": "المجموع الفرعي",
        "shipping": "الشحن",
        "total": "الإجمالي",
        "email": "البريد الإلكتروني",
        "pay_now": "ادفع الآن",
        "success": "تم إكمال الدفع",
        "cancel": "تم إلغاء الدفع",
        "back": "العودة للمتجر",
        "products": "المنتجات",
        "details": "تفاصيل المنتج",
        "language": "English",
        "newsletter_title": "ابقَ على اطلاع",
        "newsletter_text": "اختيارات جديدة وتنبيهات خفيفة وقت الحاجة.",
        "subscribe": "اشترك",
        "footer_note": "موجودين دائمًا لخدمتك — تسوّق بثقة وراحة",
        "comments": "التعليقات",
        "add_comment": "أضف تعليقك",
        "name": "الاسم",
        "comment": "التعليق",
        "edit": "تعديل",
        "delete": "حذف",
        "save": "حفظ",
    },
}


PRODUCTS_SEED = [
    {
        "sku": "AUR-HEAD-01",
        "name_en": "Nebula Headset",
        "name_ar": "سماعة نيبولا",
        "price_cents": 12900,
        "image": "https://images.unsplash.com/photo-1512446816042-444d641267bc?q=80&w=900&auto=format&fit=crop",
        "category_en": "Audio",
        "category_ar": "صوتيات",
        "badge_en": "New",
        "badge_ar": "جديد",
        "description_en": "Spatial audio and deep bass in a sleek, matte shell.",
        "description_ar": "صوت محيطي وباس عميق في تصميم أنيق.",
    },
    {
        "sku": "AUR-WATCH-02",
        "name_en": "Pulse Watch",
        "name_ar": "ساعة بلس",
        "price_cents": 9900,
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=900&auto=format&fit=crop",
        "category_en": "Wearables",
        "category_ar": "إكسسوارات",
        "badge_en": "Limited",
        "badge_ar": "محدود",
        "description_en": "Ultra smooth display and a battery that keeps up.",
        "description_ar": "شاشة انسيابية وبطارية تدوم طوال اليوم.",
    },
    {
        "sku": "AUR-CAM-03",
        "name_en": "Lumen Camera",
        "name_ar": "كاميرا لومن",
        "price_cents": 15900,
        "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=900&auto=format&fit=crop",
        "category_en": "Cameras",
        "category_ar": "كاميرات",
        "badge_en": "Pro",
        "badge_ar": "احترافي",
        "description_en": "Capture every highlight with cinematic clarity.",
        "description_ar": "التقط كل لحظة بوضوح سينمائي.",
    },
    {
        "sku": "AUR-SPEAK-04",
        "name_en": "Aura Speaker",
        "name_ar": "سماعة أورا",
        "price_cents": 8400,
        "image": "https://images.unsplash.com/photo-1519677100203-a0e668c92439?q=80&w=900&auto=format&fit=crop",
        "category_en": "Audio",
        "category_ar": "صوتيات",
        "badge_en": "Best seller",
        "badge_ar": "الأكثر مبيعاً",
        "description_en": "360 degree sound with a floating light ring.",
        "description_ar": "صوت محيطي مع حلقة إضاءة عائمة.",
    },
    {
        "sku": "AUR-LAP-05",
        "name_en": "Nova Laptop",
        "name_ar": "نوفا لابتوب",
        "price_cents": 189900,
        "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=900&auto=format&fit=crop",
        "category_en": "Computers",
        "category_ar": "حواسيب",
        "badge_en": "Studio",
        "badge_ar": "استوديو",
        "description_en": "Creator-grade performance in a razor-thin frame.",
        "description_ar": "أداء احترافي في هيكل فائق النحافة.",
    },
    {
        "sku": "AUR-BAG-06",
        "name_en": "Orbit Bag",
        "name_ar": "حقيبة أوربت",
        "price_cents": 7600,
        "image": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=900&auto=format&fit=crop",
        "category_en": "Accessories",
        "category_ar": "إكسسوارات",
        "badge_en": "Eco",
        "badge_ar": "صديق للبيئة",
        "description_en": "Water-resistant, minimal, and built for travel.",
        "description_ar": "مقاومة للماء وبسيطة ومناسبة للسفر.",
    },
]

EXTRA_PRODUCT_NAMES = [
    ("Solace Tablet", "تابلت سولاس"),
    ("Echo Buds", "سماعات إيكو"),
    ("Flux Keyboard", "لوحة مفاتيح فلكس"),
    ("Glide Mouse", "ماوس غلايد"),
    ("Skyline Drone", "درون سكايلاين"),
    ("Halo Lamp", "مصباح هالو"),
    ("Arc Stand", "ستاند آرك"),
    ("Pulse Charger", "شاحن بلس"),
    ("Core Bottle", "قارورة كور"),
    ("Stride Band", "سوار سترايد"),
    ("Wave Speaker", "سماعة ويف"),
    ("Prism Action Cam", "كاميرا بريزم"),
    ("Nova Monitor", "شاشة نوفا"),
    ("Orbit Dock", "محطة أوربت"),
    ("Vortex Console", "كونسول فورتكس"),
    ("Glide Pad", "باد غلايد"),
    ("Pulse Router", "راوتر بلس"),
    ("Halo Thermostat", "ثرموستات هالو"),
    ("Lumina Lens", "عدسة لومينا"),
    ("Nova Backpack", "حقيبة نوفا"),
    ("Orbit Chair", "كرسي أوربت"),
    ("Rise Desk", "مكتب رايز"),
    ("Nova Phone", "هاتف نوفا"),
    ("Shield Case", "غطاء شيلد"),
    ("Orbit Watch", "ساعة أوربت"),
    ("Volt E-Bike", "دراجة فولت"),
    ("Aura Blender", "خلاط أورا"),
    ("Nova Coffee", "ماكينة نوفا"),
    ("Echo Studio", "إيكو ستوديو"),
    ("Pulse Mic", "مايك بلس"),
    ("Lumen Notebook", "دفتر لومن"),
    ("Arc Pen", "قلم آرك"),
    ("Halo Glasses", "نظارات هالو"),
    ("Orbit Mini", "أوربت ميني"),
    ("Nova Powerbank", "باور بنك نوفا"),
    ("Astra Tripod", "ترايبود أسترا"),
    ("Echo Max", "إيكو ماكس"),
    ("Vault SSD", "قرص فولت"),
    ("Orbit Vacuum", "مكنسة أوربت"),
    ("Arc Light Bar", "شريط ضوء آرك"),
    ("Nova Cap", "قبعة نوفا"),
    ("Pulse Runners", "حذاء بلس"),
    ("Orbit Jacket", "جاكيت أوربت"),
    ("Halo Tote", "توت هالو"),
]

PRODUCT_IMAGES = [
    "https://images.unsplash.com/photo-1512446816042-444d641267bc?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519677100203-a0e668c92439?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1473968512647-3e447244af8f?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507494924047-60b8ee826ca9?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1542751110-97427bbecf20?q=80&w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?q=80&w=900&auto=format&fit=crop",
]

CATEGORIES = [
    ("Audio", "صوتيات"),
    ("Wearables", "إكسسوارات"),
    ("Cameras", "كاميرات"),
    ("Computers", "حواسيب"),
    ("Accessories", "إكسسوارات"),
    ("Gaming", "ألعاب"),
    ("Home", "منزل"),
    ("Office", "مكتب"),
    ("Smart", "ذكي"),
    ("Fitness", "لياقة"),
]

BADGES = [
    ("New", "جديد"),
    ("Limited", "محدود"),
    ("Pro", "احترافي"),
    ("Eco", "صديق للبيئة"),
    ("Studio", "استوديو"),
    ("Best seller", "الأكثر مبيعاً"),
    ("Ultra", "فائق"),
    ("Compact", "مضغوط"),
    ("Glow", "متوهج"),
    ("Prime", "برايم"),
]

DESCRIPTIONS = [
    ("Precision-made for daily power.", "مصمم بدقة لقوة يومية."),
    ("Smooth design with bold performance.", "تصميم ناعم مع أداء قوي."),
    ("Lightweight build, premium finish.", "هيكل خفيف وتشطيب فاخر."),
    ("Engineered for speed and clarity.", "مصمم للسرعة والوضوح."),
    ("Clean lines with soft-touch feel.", "خطوط نظيفة وملمس ناعم."),
    ("Balanced performance for modern life.", "أداء متوازن لحياة عصرية."),
    ("Minimal form, maximum impact.", "بساطة في الشكل وتأثير كبير."),
    ("Quiet power with elegant control.", "قوة هادئة وتحكم أنيق."),
]

BASE_PRICES = [2900, 3600, 5200, 6900, 8400, 9900, 12900, 15900, 21900, 29900, 44900, 69900]


def build_extra_products(start_index: int = 7):
    items = []
    for i, (name_en, name_ar) in enumerate(EXTRA_PRODUCT_NAMES, start=start_index):
        category_en, category_ar = CATEGORIES[(i - 1) % len(CATEGORIES)]
        badge_en, badge_ar = BADGES[(i - 1) % len(BADGES)]
        desc_en, desc_ar = DESCRIPTIONS[(i - 1) % len(DESCRIPTIONS)]
        image = PRODUCT_IMAGES[(i - 1) % len(PRODUCT_IMAGES)]
        price_cents = BASE_PRICES[(i - 1) % len(BASE_PRICES)]
        items.append(
            {
                "sku": f"AUR-PRD-{i:02d}",
                "name_en": name_en,
                "name_ar": name_ar,
                "price_cents": price_cents,
                "image": image,
                "category_en": category_en,
                "category_ar": category_ar,
                "badge_en": badge_en,
                "badge_ar": badge_ar,
                "description_en": desc_en,
                "description_ar": desc_ar,
            }
        )
    return items


PRODUCTS_SEED.extend(build_extra_products())


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def send_payment_email(to_email: str):
    if not (EMAIL_USER and EMAIL_APP_PASSWORD):
        print("EMAIL ERROR: missing EMAIL_USER or EMAIL_APP_PASSWORD", file=sys.stderr)
        return False
    msg = EmailMessage()
    msg["Subject"] = "تأكيد الدفع — شكراً لتسوقك معنا"
    msg["From"] = f"{EMAIL_SENDER_NAME} <{EMAIL_USER}>"
    msg["To"] = to_email
    msg.set_content(
        "\n".join(
            [
                f"مرحباً،",
                "",
                "تم إكمال عملية الدفع بنجاح. نشكرك على ثقتك وتسوقك معنا.",
                "نحن نجهّز طلبك الآن، وسنرسل لك تحديثاً فور تجهيز الشحنة.",
                "",
                "لو عندك أي سؤال أو تحتاج مساعدة، تقدر ترد على هذا الإيميل مباشرة.",
                "",
                "تحياتنا،",
                EMAIL_SENDER_NAME,
            ]
        )
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print(f"EMAIL ERROR: {exc}", file=sys.stderr)
        return False


@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    resp.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    return resp


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name_en TEXT NOT NULL,
            name_ar TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            image TEXT NOT NULL,
            category_en TEXT,
            category_ar TEXT,
            badge_en TEXT,
            badge_ar TEXT,
            description_en TEXT,
            description_ar TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            total_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            stripe_session_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_cents INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    for item in PRODUCTS_SEED:
        cur.execute(
            """
            INSERT INTO products (
                sku, name_en, name_ar, price_cents, image,
                category_en, category_ar, badge_en, badge_ar,
                description_en, description_ar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                name_en=excluded.name_en,
                name_ar=excluded.name_ar,
                price_cents=excluded.price_cents,
                image=excluded.image,
                category_en=excluded.category_en,
                category_ar=excluded.category_ar,
                badge_en=excluded.badge_en,
                badge_ar=excluded.badge_ar,
                description_en=excluded.description_en,
                description_ar=excluded.description_ar
            """,
            (
                item["sku"],
                item["name_en"],
                item["name_ar"],
                item["price_cents"],
                item["image"],
                item["category_en"],
                item["category_ar"],
                item["badge_en"],
                item["badge_ar"],
                item["description_en"],
                item["description_ar"],
            ),
        )
    conn.commit()
    conn.close()


def get_lang():
    lang = request.args.get("lang") or session.get("lang") or "ar"
    if lang not in ("ar", "en"):
        lang = "ar"
    session["lang"] = lang
    return lang


def get_session_id() -> str:
    sid = session.get("sid")
    if not sid:
        sid = os.urandom(8).hex()
        session["sid"] = sid
    return sid


def fetch_products() -> List[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_product(pid: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (pid,))
    row = cur.fetchone()
    conn.close()
    return row


def fetch_comments(pid: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, product_id, session_id, author, content, created_at FROM comments WHERE product_id = ? ORDER BY id DESC",
        (pid,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_cart() -> Dict[str, int]:
    return session.get("cart", {})


def set_cart(cart: Dict[str, int]):
    session["cart"] = cart
    session.modified = True


def cart_items():
    cart = get_cart()
    items = []
    total_cents = 0
    for pid, qty in cart.items():
        product = fetch_product(int(pid))
        if not product:
            continue
        line_total = product["price_cents"] * qty
        total_cents += line_total
        items.append({
            "product": product,
            "qty": qty,
            "line_total": line_total,
        })
    return items, total_cents


@app.route("/")
def index():
    lang = get_lang()
    products = fetch_products()
    return render_template(
        "index.html",
        lang=lang,
        t=TEXT[lang],
        products=products,
        cart_count=sum(get_cart().values()),
    )


@app.route("/product/<int:pid>")
def product(pid: int):
    lang = get_lang()
    sid = get_session_id()
    item = fetch_product(pid)
    if not item:
        abort(404)
    comments = fetch_comments(pid)
    return render_template(
        "product.html",
        lang=lang,
        t=TEXT[lang],
        product=item,
        comments=comments,
        can_edit_sid=sid,
        cart_count=sum(get_cart().values()),
    )


@app.route("/cart")
def cart():
    lang = get_lang()
    items, total_cents = cart_items()
    return render_template(
        "cart.html",
        lang=lang,
        t=TEXT[lang],
        items=items,
        total_cents=total_cents,
        currency=CURRENCY,
        cart_count=sum(get_cart().values()),
    )


@app.route("/checkout")
def checkout():
    lang = get_lang()
    items, total_cents = cart_items()
    return render_template(
        "checkout.html",
        lang=lang,
        t=TEXT[lang],
        items=items,
        total_cents=total_cents,
        currency=CURRENCY,
        cart_count=sum(get_cart().values()),
        stripe_publishable_key=STRIPE_PUBLISHABLE_KEY,
        stripe_configured=bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY),
    )


@app.post("/api/cart/add")
def api_cart_add():
    data = request.get_json(silent=True) or {}
    pid = str(data.get("product_id"))
    qty = int(data.get("qty", 1))
    if not pid.isdigit():
        return jsonify({"ok": False}), 400

    cart = get_cart()
    cart[pid] = cart.get(pid, 0) + max(qty, 1)
    set_cart(cart)
    return jsonify({"ok": True, "count": sum(cart.values())})


@app.post("/api/cart/remove")
def api_cart_remove():
    data = request.get_json(silent=True) or {}
    pid = str(data.get("product_id"))
    cart = get_cart()
    if pid in cart:
        cart.pop(pid)
        set_cart(cart)
    return jsonify({"ok": True, "count": sum(cart.values())})


@app.post("/api/cart/clear")
def api_cart_clear():
    set_cart({})
    return jsonify({"ok": True, "count": 0})


@app.post("/create-checkout-session")
def create_checkout_session():
    if not (STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY):
        # Simulated payment flow: send email confirmation and go to success page
        lang = get_lang()
        email = request.form.get("email")
        if email:
            send_payment_email(email)
        return redirect(url_for("checkout_success", lang=lang))

    stripe.api_key = STRIPE_SECRET_KEY
    lang = get_lang()
    email = request.form.get("email")
    items, total_cents = cart_items()

    if not items:
        return redirect(url_for("cart", lang=lang))

    line_items = []
    for entry in items:
        product = entry["product"]
        line_items.append(
            {
                "price_data": {
                    "currency": CURRENCY.lower(),
                    "product_data": {
                        "name": product["name_en"],
                    },
                    "unit_amount": product["price_cents"],
                },
                "quantity": entry["qty"],
            }
        )

    session_obj = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        customer_email=email,
        success_url=url_for("checkout_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}&lang=" + lang,
        cancel_url=url_for("checkout_cancel", _external=True) + "?lang=" + lang,
    )

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (email, total_cents, currency, status, stripe_session_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (email, total_cents, CURRENCY, "pending", session_obj.id, datetime.utcnow().isoformat()),
    )
    order_id = cur.lastrowid
    for entry in items:
        cur.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity, price_cents)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, entry["product"]["id"], entry["qty"], entry["product"]["price_cents"]),
        )
    conn.commit()
    conn.close()

    return redirect(session_obj.url)


@app.post("/product/<int:pid>/comments")
def add_comment(pid: int):
    lang = get_lang()
    sid = get_session_id()
    author = (request.form.get("author") or "").strip()
    content = (request.form.get("content") or "").strip()
    if not author or not content:
        flash("اكتب الاسم والتعليق لو سمحت." if lang == "ar" else "Please add your name and comment.", "error")
        return redirect(url_for("product", pid=pid, lang=lang))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO comments (product_id, session_id, author, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (pid, sid, author[:60], content[:800], datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("product", pid=pid, lang=lang))


@app.post("/comment/<int:cid>/edit")
def edit_comment(cid: int):
    lang = get_lang()
    sid = get_session_id()
    content = (request.form.get("content") or "").strip()
    pid = int(request.form.get("product_id") or 0)
    if not content:
        return redirect(url_for("product", pid=pid, lang=lang))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE comments SET content = ? WHERE id = ? AND session_id = ?",
        (content[:800], cid, sid),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("product", pid=pid, lang=lang))


@app.post("/comment/<int:cid>/delete")
def delete_comment(cid: int):
    lang = get_lang()
    sid = get_session_id()
    pid = int(request.form.get("product_id") or 0)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM comments WHERE id = ? AND session_id = ?", (cid, sid))
    conn.commit()
    conn.close()
    return redirect(url_for("product", pid=pid, lang=lang))


@app.route("/success")
def checkout_success():
    lang = get_lang()
    set_cart({})
    return render_template("success.html", lang=lang, t=TEXT[lang])


@app.route("/cancel")
def checkout_cancel():
    lang = get_lang()
    return render_template("cancel.html", lang=lang, t=TEXT[lang])


@app.post("/webhook")
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return "", 400

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        return "", 400

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET status = ? WHERE stripe_session_id = ?",
            ("paid", session_obj["id"]),
        )
        conn.commit()
        conn.close()

    return "", 200


if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    init_db()
    app.run(debug=False)
