import frappe
from frappe.sessions import get_csrf_token


@frappe.whitelist(allow_guest=True)
def me():
    """Identity for the SPA. Logged-in sessions get a CSRF token, because sessions
    created by /api/method/login do not have one saved and Frappe then skips the check."""
    user = frappe.session.user
    if user == "Guest":
        return {"user": None}
    asset_write = bool(frappe.has_permission("Asset", "write"))
    team_read = bool(frappe.has_permission("Asset Maintenance Team", "read"))
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name"),
        "csrf_token": get_csrf_token(),
        "roles": frappe.get_roles(user),
        "can": {
            ptype: bool(frappe.has_permission("Asset", ptype))
            for ptype in ("read", "write", "create", "submit")
        },
        # Each flag is true only when the endpoint it opens would accept the request. Changes to an
        # asset need write on the Asset plus create on the doctype the endpoint creates. The UI uses
        # these only to decide what to show; real enforcement stays in those endpoints.
        "features": {
            "asset_list": bool(frappe.has_permission("Asset", "read")),
            "asset_create": bool(frappe.has_permission("Asset", "create"))
            and bool(frappe.has_permission("Asset Movement", "create"))
            and bool(frappe.has_permission("Company", "read")),
            "asset_movement": asset_write and bool(frappe.has_permission("Asset Movement", "create")),
            "asset_repair": asset_write and bool(frappe.has_permission("Asset Repair", "create")),
            "maintenance_plan": asset_write and team_read
            and bool(frappe.has_permission("Asset Maintenance", "create")),
            "maintenance_team": team_read,
        },
    }
