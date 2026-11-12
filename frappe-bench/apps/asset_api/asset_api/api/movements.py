import frappe

from asset_api.api._common import ErrorCode, get_asset, require_csrf_token

PURPOSES = ("Transfer", "Issue", "Receipt", "Transfer and Issue")
MAX_ASSETS = 50


@frappe.whitelist(methods=["POST"])
def create(assets: list[str], purpose: str = "Transfer", target_location: str | None = None,
           to_employee: str | None = None, submit: bool = True):
    """Create (and by default submit) an Asset Movement built by ERPNext's mapper."""
    from erpnext.assets.doctype.asset.mapper import make_asset_movement

    require_csrf_token()
    if purpose not in PURPOSES:
        frappe.throw(f"{ErrorCode.INVALID}: purpose {purpose}", frappe.ValidationError)
    assets = list(dict.fromkeys(a for a in assets if a))  # de-duplicate, drop empty names
    if not 1 <= len(assets) <= MAX_ASSETS:
        frappe.throw(f"{ErrorCode.INVALID}: assets must contain 1 to {MAX_ASSETS} names", frappe.ValidationError)
    if purpose in ("Transfer", "Receipt", "Transfer and Issue") and not target_location:
        frappe.throw(f"{ErrorCode.INVALID}: target_location is required", frappe.ValidationError)
    if purpose in ("Issue", "Transfer and Issue") and not to_employee:
        frappe.throw(f"{ErrorCode.INVALID}: to_employee is required", frappe.ValidationError)
    for name in assets:
        get_asset(name, "write")
    for dt, val in (("Location", target_location), ("Employee", to_employee)):
        if val and not frappe.has_permission(dt, "read", val):
            frappe.throw(f"{ErrorCode.FORBIDDEN}: {dt} {val}", frappe.PermissionError)
    needed = ("create", "submit") if submit else ("create",)
    for ptype in needed:
        if not frappe.has_permission("Asset Movement", ptype):
            frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Movement {ptype}", frappe.PermissionError)

    draft = make_asset_movement([{"name": n} for n in assets], purpose)
    doc = frappe.get_doc(draft)
    for row in doc.assets:
        if target_location:
            row.target_location = target_location
        if to_employee:
            row.to_employee = to_employee
    doc.insert()
    if submit:
        doc.submit()
    return {"name": doc.name, "docstatus": doc.docstatus, "purpose": doc.purpose}
