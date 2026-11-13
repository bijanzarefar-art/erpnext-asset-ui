# رابط راست‌به‌چپ مدیریت دارایی برای ERPNext

رابط فارسی و headless برای ماژول Asset در ERPNext نسخه ۱۷. دو بخش دارد:

| بخش | مسیر | کار |
|---|---|---|
| `asset_api` | `frappe-bench/apps/asset_api` | اپ Frappe با متدهای whitelisted؛ همه بررسی‌های دسترسی اینجاست |
| `asset-ui` | `asset-ui/` | Vue 3 + frappe-ui + Tailwind، ساخته‌شده با Vite؛ فقط نمایش |

احراز هویت با کوکی نشست Frappe است. مرورگر هیچ API key ندارد و رابط و Frappe روی یک دامنه سرو می‌شوند،
پس CORS لازم نیست و نباید فعال شود.

## ۱) پیش‌نیازها

- یک bench کارکرده با Frappe و ERPNext نسخه ۱۷ و یک سایت که setup wizard آن تمام شده باشد
  (شرکت، سال مالی، واحد پول).
- Node.js 20 یا بالاتر برای ساخت فرانت.
- nginx و گواهی TLS برای استقرار.

## ۲) نصب بک‌اند روی یک سایت

```bash
cd /path/to/frappe-bench
# bench get-app <آدرس مخزن git اپ asset_api>   # این پروژه هنوز آدرس مخزن ندارد؛ تا آن زمان اپ باید در apps/ و sites/apps.txt باشد
bench --site SITE_NAME install-app asset_api
cd sites && ../env/bin/python -m frappe.utils.bench_helper frappe --site SITE_NAME migrate && cd ..
bench restart                              # در production (supervisor/systemd)
```

`asset_api` دکتایپ یا فیلد جدیدی نمی‌سازد و به داده‌ها دست نمی‌زند؛ فقط متد اضافه می‌کند.

راستی‌آزمایی:

```bash
bench --site SITE_NAME set-config allow_tests true    # فقط روی سایت آزمایشی
bench --site SITE_NAME run-tests --app asset_api      # انتظار: 48 تست، OK
```

تست‌ها داده موقت می‌سازند و خودشان پاک می‌کنند. آن‌ها را روی سایت production اجرا نکنید.

## ۳) ساخت و سرو فرانت

```bash
cd asset-ui
npm ci
npm run build:deploy        # خروجی dist/ با پایه /asset-ui/
```

`dist/` را روی سرور کپی کنید (مثلاً `/opt/asset-ui/dist`) و فایل نمونه
[`deploy/nginx/asset-ui.conf`](deploy/nginx/asset-ui.conf) را با این جایگزینی‌ها به nginx اضافه کنید:

| در فایل نمونه | جایگزین با |
|---|---|
| `assets.example.com` | دامنه شما = نام سایت Frappe |
| `/opt/bench` | مسیر frappe-bench |
| `/opt/asset-ui/dist` | مسیر dist |
| `127.0.0.1:8000` و `127.0.0.1:9000` | `webserver_port` و `socketio_port` در `common_site_config.json` |

**جای فایل مهم است.** این فایل یک بلوک کامل برای context اصلی `http` است و `upstream` دارد.
آن را در `/etc/nginx/conf.d/asset-ui.conf` بگذارید (nginx خودش `conf.d/*.conf` را داخل `http` می‌خواند).
اگر آن را با `include` داخل یک `server` بگذارید، nginx با خطای
`upstream directive is not allowed here` رد می‌کند.

```bash
sudo cp deploy/nginx/asset-ui-security-headers.conf /etc/nginx/snippets/
sudo cp deploy/nginx/asset-ui.conf /etc/nginx/conf.d/asset-ui.conf
sudo nginx -t && sudo systemctl reload nginx
```

فایل نمونه به nginx نسخه 1.25.1 یا بالاتر نیاز دارد (`http2 on` و `ssl_reject_handshake`). یک بلوک
`default_server` هم دارد که درخواست با Host ناشناخته را رد می‌کند. اگر سرور شما بلوک پیش‌فرض دیگری دارد،
یکی از آن دو را حذف کنید.

آدرس رابط: `https://DOMAIN/asset-ui/`. Desk خود ERPNext همچنان روی `https://DOMAIN/app` است.

`bench build` برای این رابط لازم نیست. اگر bench شما خودش فایل nginx تولید می‌کند
(`bench setup nginx`)، فقط بلوک‌های `location /asset-ui` نمونه را به آن اضافه کنید و بقیه را دست نزنید.

### تست محلی nginx

برای آزمودن پیکربندی روی همین ماشین، بدون گواهی TLS و بدون دست‌زدن به فایل نمونه:

```bash
brew install nginx
nginx -t -c "$PWD/deploy/nginx/local-test-wrapper.conf"
nginx -c "$PWD/deploy/nginx/local-test-wrapper.conf" -p "$PWD"
# http://asset.localhost:8090/asset-ui/
nginx -s stop -c "$PWD/deploy/nginx/local-test-wrapper.conf" -p "$PWD"
```

`local-test.conf` همان بلوک‌های نمونه را با مسیرهای واقعی و پورت 8090 دارد و
`local-test-wrapper.conf` آن را داخل `http` می‌گذارد. این دو فقط برای تست‌اند و در استقرار استفاده نمی‌شوند.

### امنیت نشست

| ویژگی کوکی `sid` | وضعیت |
|---|---|
| HttpOnly | همیشه (Frappe) |
| SameSite=Lax | همیشه (Frappe) |
| Secure | فقط وقتی Frappe درخواست را HTTPS ببیند |

برای Secure، nginx هدر `X-Forwarded-Proto` را می‌فرستد و gunicorn باید آن را بپذیرد. پیش‌فرض gunicorn
فقط به `127.0.0.1` اعتماد می‌کند، که وقتی nginx روی همان ماشین است کافی است. بعد از استقرار بررسی کنید:

```bash
curl -sI https://DOMAIN/api/method/asset_api.api.session.me | grep -i set-cookie
# انتظار: sid=...; ... HttpOnly; Path=/; SameSite=Lax; Secure
```

`allow_cors` را در `site_config.json` تنظیم نکنید. Frappe با هر مقدار آن
`Access-Control-Allow-Credentials: true` می‌فرستد.

نوشتن‌ها توکن CSRF می‌خواهند: `session.me` توکن را می‌سازد و برمی‌گرداند، و هر متد نوشتن نشستی را که توکن
ذخیره‌شده ندارد رد می‌کند.

## ۴) نقش‌ها

همه از نقش‌های استاندارد ERPNext است؛ نقش سفارشی لازم نیست. منو و دکمه‌ها از `session.me` → `features`
تعیین می‌شوند، ولی اعمال واقعی دسترسی در خود متدهای سرور است.

جدول زیر از نتیجه آزمون واقعی روی سایت آزمایشی در ERPNext 17 ساخته شده است، نه فقط از DocPerm. هر ردیف یک نقش یا ترکیب نقش است و
ستون‌ها کاری است که رابط نشان می‌دهد و سرور می‌پذیرد. System Manager و Administrator همه کارها را دارند.

| نقش یا ترکیب | کارهای مجاز |
|---|---|
| Accounts User | داشبورد و فهرست، ثبت تعمیر، تکمیل تعمیر |
| Accounts User + Accounts Manager یا Stock Manager | همه بالا، به‌علاوه ثبت دارایی جدید، جابه‌جایی و اسقاط |
| Quality Manager | داشبورد و فهرست، ثبت تعمیر، تکمیل تعمیر |
| Manufacturing User | فقط مشاهده تیم نگهداری؛ ثبت تعمیر و جابه‌جایی ممکن نیست |
| Accounts User + Manufacturing User | ثبت تعمیر و تکمیل آن، ساخت برنامه نگهداری، مشاهده تیم و لاگ‌ها |
| Stock Manager یا Accounts Manager به‌تنهایی | بدون دسترسی؛ باید با Accounts User یا Quality Manager ترکیب شوند |
| Stock User | بدون دسترسی به دکتایپ دارایی |

نکته‌ها:

- جابه‌جایی و ثبت دارایی جدید هر دو نیاز به دسترسی **write روی دارایی** دارند، و این دسترسی را Accounts User یا Quality Manager دارد.
- ساخت برنامه نگهداری هم نیاز به دسترسی write روی دارایی دارد و هم نقش Manufacturing User (یا دسترسی خواندن تیم).
- اگر کاربری فقط Stock Manager است و باید جابه‌جایی انجام دهد، یکی از نقش‌های Accounts User یا Quality Manager را هم به او بدهید.

نقش‌ها را در Desk از **User → Roles** بدهید. رابط دکمه‌ها را با همین بررسی‌ها نشان می‌دهد (`session.me` → `features`)،
و هر متد سرور هم همان را دوباره بررسی می‌کند؛ بنابراین کاربری که دکمه نمی‌بیند، آن کار را از سرور هم نمی‌تواند انجام دهد.

## ۵) محدود کردن کاربر به یک محل (User Permission)

بدون کد سفارشی، با ابزار خود Frappe:

1. Desk → **User Permission** → New
2. User = کاربر، Allow = **Location**، For Value = محل مجاز، Apply To All Document Types = تیک
3. ذخیره

از این به بعد داشبورد، فهرست، جزئیات، جابه‌جایی و نگهداری برای آن کاربر فقط دارایی‌های همان محل و
زیرمحل‌هایش را نشان می‌دهند. باز کردن مستقیم دارایی محل دیگر، پیام «دسترسی ندارید» می‌دهد.
تست مربوط: `asset_api/tests/test_api.py` کلاس `TestLocationScoping`.

### محدودیت‌های شناخته‌شده این محدودسازی

این موارد با تست واقعی تأیید شده‌اند و خودشان اشکال امنیتی نیستند، ولی تجربه کاربر را تحت تأثیر می‌گذارند:

- **دکمه‌ها به محل خاص نگاه نمی‌کنند.** `session.me` → `features` در سطح کل سایت سنجیده می‌شود، چون
  کاربر هنوز محل مقصد را انتخاب نکرده است. پس کاربری که به «دفتر مرکزی» محدود است، دکمه «ثبت دارایی
  جدید» و «جابه‌جایی» را می‌بیند، ولی اگر محل دیگری را انتخاب کند، سرور همان لحظه رد می‌کند.
  تست: `TestLocationSpecificChecks` و `TestFeatureFlagsUnderLocationScope`.
- **پاسخ خطا گویا نیست.** سرور درست رد می‌کند، ولی پیام دقیق «این محل برای شما مجاز نیست» به رابط نمی‌رسد.
  کاربر پیام کلی می‌بیند. این مورد برای نسخه بعدی گذاشته شده است.
- **ثبت دارایی جدید برای کاربر محل‌محدود کار نمی‌کند.** ثبت دارایی، در ERPNext، یک «Asset Movement» اولیه
  می‌سازد و آن جابه‌جایی برای کاربر محدود به محل، رد می‌شود. برای این کاربران از Desk استفاده کنید،
  یا نقش کاربر را موقتاً کامل کنید.

## ۶) نسخه پشتیبان و بازگردانی

همه داده‌ها در دیتابیس و فایل‌های سایت ERPNext است. رابط داده‌ای جدا ندارد.

```bash
cd /path/to/frappe-bench
bench --site SITE_NAME backup --with-files --compress
# خروجی در sites/SITE_NAME/private/backups/
```

- خروجی را به جای دیگری منتقل کنید (دیسک یا سرور جدا). پشتیبان روی همان دیسک کافی نیست.
- `sites/SITE_NAME/site_config.json` را هم جدا نگه دارید. `encryption_key` داخل آن برای
  بازگردانی رمزهای ذخیره‌شده لازم است.
- زمان‌بندی: Frappe خودش پشتیبان دوره‌ای نمی‌گیرد. دستور `bench setup backups` یک کار cron هر ۶ ساعت برای همه سایت‌ها اضافه می‌کند (لاگ در `logs/backup.log`).

بازگردانی، که داده فعلی سایت را جایگزین می‌کند:

```bash
bench --site SITE_NAME restore PATH/database.sql.gz \
  --with-public-files PATH/files.tar --with-private-files PATH/private-files.tar
cd sites && ../env/bin/python -m frappe.utils.bench_helper frappe --site SITE_NAME migrate && cd ..
```

فرانت داده ندارد. برای بازسازی، کافی است `npm run build:deploy` دوباره اجرا شود.

## ۷) توسعه محلی

راهنمای اجرای Vite و پروکسی در [`asset-ui/README.md`](asset-ui/README.md) است.
روند کار و مراحل در [`execplan.md`](execplan.md) و نقش عامل‌ها در [`ORCHESTRATION.md`](ORCHESTRATION.md).

## محدودیت‌های شناخته‌شده

- ERPNext نسخه ۱۷ هنوز develop است و ممکن است فیلدها تغییر کنند. بعد از هر به‌روزرسانی، تست‌ها را اجرا کنید.
- هزینه تعمیر از فاکتور خرید می‌آید و ثبت فاکتور در این رابط نیست.
- ایمیل و اعلان‌های ERPNext تنظیم و آزمون نشده‌اند.
