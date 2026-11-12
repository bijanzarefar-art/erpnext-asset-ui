import frappe
from frappe.utils import add_days, nowdate

CO = "شرکت آزمایشی دارایی"
USER = "asset.ui.test@example.com"
ASSET = "ACC-ASS-2026-00001"
TEAM = "تیم نگهداری آزمایشی"

if not frappe.db.exists("Asset Maintenance Team", TEAM):
    frappe.get_doc({"doctype": "Asset Maintenance Team", "maintenance_team_name": TEAM, "company": CO,
                    "maintenance_manager": USER,
                    "maintenance_team_members": [{"team_member": USER, "maintenance_role": "Manufacturing User"}]}).insert()

if not frappe.db.exists("Asset Maintenance", ASSET):
    frappe.get_doc({"doctype": "Asset Maintenance", "asset_name": ASSET, "company": CO, "maintenance_team": TEAM,
                    "asset_maintenance_tasks": [
                        {"maintenance_task": "روغن‌کاری و بازرسی", "maintenance_type": "Preventive Maintenance",
                         "periodicity": "Monthly", "start_date": add_days(nowdate(), -45), "assign_to": USER,
                         "maintenance_status": "Planned"},
                        {"maintenance_task": "کالیبراسیون سالانه", "maintenance_type": "Calibration",
                         "periodicity": "Yearly", "start_date": add_days(nowdate(), 5), "assign_to": USER,
                         "maintenance_status": "Planned"},
                    ]}).insert()
frappe.db.commit()
print("PLAN", frappe.db.exists("Asset Maintenance", ASSET))
print("LOGS", frappe.get_all("Asset Maintenance Log", filters={"asset_maintenance": ASSET},
      fields=["name", "task_name", "due_date", "maintenance_status", "docstatus"]))
