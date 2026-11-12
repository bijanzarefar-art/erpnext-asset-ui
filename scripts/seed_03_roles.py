import frappe
u = frappe.get_doc("User", "asset.ui.test@example.com")
if "Manufacturing User" not in [r.role for r in u.roles]:
    u.append("roles", {"role": "Manufacturing User"})
    u.save()
    frappe.db.commit()
print("ROLES", sorted(r.role for r in u.roles))
