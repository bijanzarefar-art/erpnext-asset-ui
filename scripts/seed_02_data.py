import frappe, secrets, os
from frappe.utils import add_days, add_months, nowdate

def _project_root() -> str:
    import os
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))



CO = "شرکت آزمایشی دارایی"
g = lambda **f: frappe.db.get_value("Account", {"company": CO, "is_group": 0, **f}, "name")
fixed = g(account_type="Fixed Asset")
accum = g(account_type="Accumulated Depreciation")
expense = g(account_type="Depreciation")
cwip = g(account_type="Capital Work in Progress")
print("ACCOUNTS", fixed, accum, expense, cwip)
assert fixed and accum and expense, "missing depreciation accounts"

for loc in ("دفتر مرکزی", "انبار تهران"):
    if not frappe.db.exists("Location", loc):
        frappe.get_doc({"doctype": "Location", "location_name": loc}).insert()

if not frappe.db.exists("Asset Category", "تجهیزات اداری"):
    frappe.get_doc({
        "doctype": "Asset Category", "asset_category_name": "تجهیزات اداری",
        "accounts": [{"company_name": CO, "fixed_asset_account": fixed,
                      "accumulated_depreciation_account": accum,
                      "depreciation_expense_account": expense,
                      "capital_work_in_progress_account": cwip}],
        "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 12,
                           "frequency_of_depreciation": 1}],
    }).insert()

items = {"ASSET-LAPTOP": "لپ‌تاپ", "ASSET-PRINTER": "پرینتر", "ASSET-DESK": "میز اداری"}
for code, name in items.items():
    if not frappe.db.exists("Item", code):
        frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name,
                        "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                        "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": "تجهیزات اداری",
                        "stock_uom": "Nos"}).insert()

def mkuser(email, first, roles):
    pw = secrets.token_urlsafe(10)
    if frappe.db.exists("User", email):
        return None
    frappe.get_doc({"doctype": "User", "email": email, "first_name": first, "send_welcome_email": 0,
                    "enabled": 1, "new_password": pw,
                    "roles": [{"role": r} for r in roles if frappe.db.exists("Role", r)]}).insert()
    return pw

pw1 = mkuser("asset.ui.test@example.com", "Asset UI Test", ["Accounts User", "Accounts Manager", "Stock User"])
pw2 = mkuser("asset.ui.norole@example.com", "Asset UI NoRole", [])
with open(os.path.join(_project_root(), ".secrets.env"), "a") as f:
    if pw1: f.write(f"TEST_USER=asset.ui.test@example.com\nTEST_USER_PASSWORD={pw1}\n")
    if pw2: f.write(f"NOROLE_USER=asset.ui.norole@example.com\nNOROLE_USER_PASSWORD={pw2}\n")

specs = [("ASSET-LAPTOP", "لپ‌توپ مدیریت", "دفتر مرکزی", 90000000, True),
         ("ASSET-PRINTER", "پرینتر شبکه", "دفتر مرکزی", 35000000, False),
         ("ASSET-DESK", "میز کنفرانس", "انبار تهران", 60000000, False)]
for item, name, loc, amt, depr in specs:
    if frappe.db.exists("Asset", {"asset_name": name}):
        continue
    d = {"doctype": "Asset", "asset_name": name, "item_code": item, "asset_category": "تجهیزات اداری",
         "company": CO, "location": loc, "asset_type": "Existing Asset",
         "purchase_date": add_days(nowdate(), -120), "available_for_use_date": add_days(nowdate(), -100),
         "net_purchase_amount": amt, "asset_quantity": 1, "calculate_depreciation": 1 if depr else 0}
    if depr:
        d["finance_books"] = [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 12,
                               "frequency_of_depreciation": 1, "depreciation_start_date": add_days(nowdate(), 20),
                               "expected_value_after_useful_life": 0}]
    a = frappe.get_doc(d).insert()
    a.submit()
    print("ASSET", a.name, a.status, a.value_after_depreciation)
frappe.db.commit()
print("DONE assets=", frappe.db.count("Asset"))
