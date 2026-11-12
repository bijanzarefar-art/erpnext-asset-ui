import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

if not frappe.is_setup_complete():
    r = setup_complete({
        "language": "English", "country": "Iran", "currency": "IRR", "timezone": "Asia/Tehran",
        "company_name": "شرکت آزمایشی دارایی", "company_abbr": "SAD",
        "chart_of_accounts": "Standard", "fy_start_date": "2026-03-21", "fy_end_date": "2027-03-20",
        "full_name": "Administrator", "email": "admin@asset.localhost",
    })
    frappe.db.commit()
    print("RESULT", r)
print("setup_complete =", frappe.is_setup_complete())
print("companies", frappe.get_all("Company", pluck="name"), "fy", frappe.get_all("Fiscal Year", pluck="name"))
