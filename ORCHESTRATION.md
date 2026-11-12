# ساختار هماهنگی عامل‌ها (Orchestration)

پروژه: رابط راست‌به‌چپ headless برای ماژول Asset در ERPNext. پلن مرجع: the plan file

## قوانین ثابت برای همه عامل‌ها
- فقط داخل `<PROJECT_ROOT>` کار کنید؛ به a separate legacy bench دست نزنید.
- دستور bench که داده را تغییر می‌دهد، فقط با تأیید صریح انسان.
- `bench build` دستی ممنوع؛ فرانت با Vite ساخته می‌شود.
- RTL: کلاس‌های منطقی Tailwind (`ms-/me-/ps-/pe-/text-start`)، مقادیر LTR داخل کلاس `ltr`، متن فارسی، تاریخ جلالی فقط در نمایش.
- اول سطوح آماده Frappe و متدهای whitelisted موجود ERPNext؛ کد جدید در آخر.
- گزارش صادقانه، از جمله آنچه تأیید نشده است.

## ۱) نقش‌ها و فازها

عامل‌های پروژه در `.claude/agents/`:
`asset-delivery-lead` (برنامه‌ریز)، `asset-api-developer` (بک‌اند)، `asset-ui-developer` (فرانت)، `asset-qa-engineer` (تست)، `frappe-security-reviewer` (امنیت).

| فاز پلن | عامل اصلی | عامل‌های پشتیبان | skillها |
|---|---|---|---|
| ۱ تثبیت خواندن (فیلدهای v17، فیلتر Active، فونت، `session.js`) | asset-ui-developer | asset-api-developer (تأیید نام فیلدها از JSON دکتایپ)، asset-qa-engineer | frappe-frontend، frappe-erpnext |
| ۲ اپ `asset_api` (session.me + CSRF، assets، movements، maintenance، reports) | asset-api-developer | frappe-security-reviewer، asset-qa-engineer، architect-reviewer (طراحی API) | frappe-backend، frappe-erpnext، frappe-sql، frappe-bench |
| ۳ عملیات نوشتن در UI (فرم‌ها، جابه‌جایی، اسقاط، داشبورد، `JalaliDateInput`) | asset-ui-developer | asset-api-developer (قرارداد API)، ui-ux-designer (چیدمان)، asset-qa-engineer | frappe-frontend، frappe-fullstack |
| ۴ کیفیت و استقرار (run-tests، Playwright RTL، nginx) | asset-qa-engineer | frappe-security-reviewer، asset-api-developer | frappe-bench، frappe-code-review |

نقش‌های عمومی (Plan، Explore، task-decomposition-expert، architect-reviewer، ui-ux-designer) برای کارهای بزرگ یا مبهم و فقط در صورت نیاز فراخوانی می‌شوند.

## ۲) حلقه استاندارد هر کار

1. **تجزیه**: `asset-delivery-lead` کار را به گام‌ها، قرارداد API و دروازه‌های تأیید می‌شکند.
2. **پیاده‌سازی**: بک‌اند اول، سپس فرانت.
3. **بازبینی**: `frappe-security-reviewer` (هر تغییر متد whitelisted/نشست) و در صورت نیاز `architect-reviewer`.
4. **تست**: `asset-qa-engineer` با bench run-tests، `npm run build` و Playwright.
5. **گزارش**: lead گزارش نهایی می‌دهد: انجام‌شده، تأییدشده با مدرک، تأییدنشده، گام بعدی.

قراردادهای تحویل:

| از | به | محتوای تحویل |
|---|---|---|
| lead | هر متخصص | هدف، فایل‌های مجاز، قرارداد (آرگومان/خروجی/خطا)، معیار پذیرش |
| api-developer | ui-developer | جدول متدها: مسیر، آرگومان، شکل خروجی، کدهای خطا، مجوز لازم |
| ui-developer | qa | فایل‌های تغییر کرده، متدهای صدا شده، نتیجه build، بخش‌های بدون بررسی بصری |
| api / ui | security-reviewer | diff یا فهرست فایل‌ها، فهرست متدهای جدید |
| qa / security | lead | حکم (PASS/FAIL یا BLOCK/OK)، جدول مدارک، نقص‌ها با مالک پیشنهادی |

نقص‌ها به مالک پیشنهادی برمی‌گردند و حلقه از گام ۲ تکرار می‌شود (حداکثر ۲ دور؛ بعد از آن به انسان ارجاع).

## ۳) موازی یا ترتیبی

- **ترتیبی**: قرارداد API ← پیاده‌سازی بک‌اند ← پیاده‌سازی UI روی قرارداد نهایی ← امنیت و تست ← گزارش.
- **موازی**: چند متد مستقل بک‌اند؛ طراحی ظاهر (ui-ux-designer) هم‌زمان با بک‌اند؛ بازبینی امنیت هم‌زمان با تست UI؛ اکتشاف‌های فقط‌خواندنی (Explore).
- **هرگز موازی**: دو عامل روی یک فایل؛ هر عملیات روی داده سایت؛ UI پیش از قطعی شدن قرارداد API.

## ۴) دروازه‌های تأیید انسانی

عامل متوقف می‌شود و می‌پرسد، پیش از:
- **ساخت داده روی سایت**: کاربر تست، Assetهای نمونه، `new-app`، `install-app`، `migrate`، `new-site`.
- **اقدام مخرب یا برگشت‌ناپذیر**: اسقاط/فروش/لغو روی رکورد واقعی، حذف، `reinstall`، `git reset`، حذف فایل.
- **هر چیز بیرون از پوشه پروژه**: خواندن یا نوشتن خارج از `<PROJECT_ROOT>`، به‌ویژه `erpnext-dev`.
- **مصرف توکن زیاد**: بیش از ۳ عامل هم‌زمان، ممیزی کلی کد، یا بازنویسی گسترده؛ ابتدا برآورد بدهید و تأیید بگیرید.
- نصب بسته جدید npm/pip و تغییر پورت/سایت هدف (`maintenance-t063.localhost`).

## ۵) سه نمونه مسیریابی

**الف) افزودن عمل «اسقاط» به صفحه جزئیات دارایی** (فاز ۳، نیازمند بک‌اند)
1. lead: قرارداد `assets.scrap(name, scrap_date)` روی `scrap_asset` و `restore_asset` ERPNext؛ دروازه: تست روی رکورد واقعی.
2. api-developer (ترتیبی): wrapper با `has_permission` روی سند، خطای با پیشوند کد، تست‌های مجوز و اسقاط/بازگردانی.
3. security-reviewer ∥ ui-developer (موازی پس از قطعی شدن قرارداد): دکمه + `Dialog` تأیید دو مرحله‌ای، `toast`، تاریخ جلالی در نمایش.
4. qa: تست‌ها و Playwright روی RTL؛ اسقاط واقعی فقط با تأیید انسان.
5. lead: گزارش و فهرست تأییدنشده‌ها.

**ب) پیاده‌سازی `session.me` با توکن CSRF** (فاز ۲، یافته امنیتی)
1. lead: قرارداد `{user, roles, permissions, csrf_token}`؛ تنها متد `allow_guest`.
2. api-developer: فراخوانی `frappe.sessions.get_csrf_token()`، برگرداندن توکن؛ تست: نوشتن بدون هدر ⇒ `CSRFTokenError`.
3. ui-developer: به‌روزرسانی `api/session.js`، تنظیم `window.csrf_token` برای `frappeRequest`؛ حذف `get_logged_user`.
4. security-reviewer (الزامی) ∥ qa: بررسی هدر روی درخواست‌های نوشتن، نبود کلید در مرورگر؛ هر دو نیاز به سایت در حال اجرا و ورود تست دارند ⇒ دروازه تأیید برای کاربر تست.
5. گزارش با مدرک درخواست/پاسخ.

**ج) افزودن فرم جابه‌جایی دارایی (Asset Movement)** (فاز ۳)
1. lead + ui-ux-designer (موازی): قرارداد `movements.create(assets, purpose, target_location, to_employee)` و چیدمان فرم.
2. api-developer: استفاده از `make_asset_movement`، سپس insert و submit؛ بررسی مجوز برای هر دارایی؛ تست.
3. ui-developer: `AssetForm`/`Movement.vue` با `Autocomplete` برای دارایی و مکان، `JalaliDateInput`؛ کلاس‌های منطقی.
4. security-reviewer ∥ qa؛ ایجاد جابه‌جایی واقعی فقط پس از تأیید انسان.
5. گزارش.
