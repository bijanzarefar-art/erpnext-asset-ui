# Asset UI

رابط کاربری headless و راست‌به‌چپ برای ماژول Asset در ERPNext.
Vue 3 + frappe-ui + Tailwind 3 + Vite. احراز هویت با session cookie.

## اجرا (توسعه)

1. bench را روی پورتی غیر از 8000 بالا بیاورید (8000 در این ماشین توسط پروژه Django اشغال است):

   ```bash
   cd <PROJECT_ROOT>/frappe-bench
   bench --site asset.localhost serve --port 8002
   ```

2. `cp .env.example .env` و در صورت نیاز `VITE_FRAPPE_SITE` را تغییر دهید.
3. `npm install && npm run dev` و باز کردن http://127.0.0.1:5173

پروکسی Vite مسیرهای `/api`، `/files` و `/socket.io` را به سایت می‌فرستد؛
بنابراین مرورگر همه‌چیز را هم‌مبدأ می‌بیند و به CORS نیازی نیست.

## ساختار

- `src/api/session.js` ورود، خروج و وضعیت نشست
- `src/utils/format.js` تاریخ جلالی، اعداد فارسی، برچسب وضعیت‌ها
- `src/views/` ورود، فهرست دارایی‌ها، جزئیات دارایی و جدول استهلاک
- `src/layouts/AppLayout.vue` سایدبار راست‌چین

## قواعد RTL

- در Tailwind به‌جای `ml-/mr-/pl-/pr-/text-left` از `ms-/me-/ps-/pe-/text-start` استفاده شود.
- مقادیر LTR مثل کد سند و ایمیل با کلاس `ltr` پوشانده شوند.
- تاریخ در دیتابیس میلادی می‌ماند و فقط در نمایش جلالی می‌شود.

## استقرار

`npm run build:deploy` خروجی `dist/` را با پایه `/asset-ui/` می‌سازد. فایل نمونه nginx در
`../deploy/nginx/asset-ui.conf` و مراحل کامل در `../README.md` است. `bench build` لازم نیست.

## محدود کردن دید دارایی‌ها

با ابزار خود Frappe انجام می‌شود، بدون کد سفارشی: در Desk بخش User Permission یک رکورد برای کاربر بسازید
(Allow = Location، For Value = محل مجاز). فهرست، داشبورد، جزئیات و جابه‌جایی همان کاربر فقط همان محل
(و زیرمحل‌هایش) را می‌بینند. تست‌ها در `asset_api/tests/test_api.py` کلاس `TestLocationScoping`.

## نقش‌های لازم

جدول کامل و دقیق (از DocPerm سایت) در `../README.md` بخش «نقش‌ها» است. خلاصه:

- دارایی‌ها: Accounts User. جابه‌جایی: Stock Manager یا Accounts Manager به‌علاوه Accounts User.
- ثبت و تکمیل تعمیر: Accounts User.
- مشاهده و تکمیل برنامه نگهداری: Manufacturing User.
