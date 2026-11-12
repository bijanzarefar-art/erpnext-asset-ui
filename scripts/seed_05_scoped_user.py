import frappe, secrets, os

def _project_root() -> str:
    import os
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))



EMAIL = "asset.ui.scoped@example.com"
pw = secrets.token_urlsafe(10)
if not frappe.db.exists("User", EMAIL):
    frappe.get_doc({
        "doctype": "User", "email": EMAIL, "first_name": "Asset UI Scoped", "send_welcome_email": 0,
        "enabled": 1, "new_password": pw,
        "roles": [{"role": r} for r in ("Accounts User", "Stock User", "Manufacturing User")
                  if frappe.db.exists("Role", r)],
    }).insert()
    with open(os.path.join(_project_root(), ".secrets.env"), "a") as f:
        f.write(f"SCOPED_USER={EMAIL}\nSCOPED_USER_PASSWORD={pw}\n")
else:
    print("user already exists; password not changed/recorded")

if not frappe.db.exists("User Permission", {"user": EMAIL, "allow": "Location", "for_value": "دفتر مرکزی"}):
    frappe.get_doc({"doctype": "User Permission", "user": EMAIL, "allow": "Location",
                    "for_value": "دفتر مرکزی", "apply_to_all_doctypes": 1}).insert()
frappe.db.commit()
print("ROLES", sorted(r.role for r in frappe.get_doc("User", EMAIL).roles))
print("PERMS", frappe.get_all("User Permission", filters={"user": EMAIL}, fields=["allow","for_value"]))
