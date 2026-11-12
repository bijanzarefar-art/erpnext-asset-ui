import frappe
from frappe.utils import flt, getdate

from asset_api.api._common import ErrorCode, get_asset, require_csrf_token

SUMMARY_FIELDS = (
    "name asset_name asset_category company location custodian status "
    "purchase_date available_for_use_date net_purchase_amount total_asset_cost "
    "value_after_depreciation journal_entry_for_scrap disposal_date docstatus"
).split()


@frappe.whitelist()
def get_summary(name: str):
    """Asset details plus the Active depreciation schedule in one call."""
    doc = get_asset(name, "read")
    summary = {f: doc.get(f) for f in SUMMARY_FIELDS}
    schedule_name = frappe.db.get_value(
        "Asset Depreciation Schedule", {"asset": name, "status": "Active"}, "name"
    )
    rows = []
    if schedule_name and frappe.has_permission("Asset Depreciation Schedule", "read", schedule_name):
        sched = frappe.get_doc("Asset Depreciation Schedule", schedule_name)
        rows = [
            {
                "schedule_date": r.schedule_date,
                "depreciation_amount": r.depreciation_amount,
                "accumulated_depreciation_amount": r.accumulated_depreciation_amount,
                "journal_entry": r.journal_entry,
            }
            for r in sched.get("depreciation_schedule")
        ]
    summary["depreciation_schedule"] = rows
    can_write = bool(frappe.has_permission("Asset", "write", doc=doc))
    not_disposed = doc.status not in ("Cancelled", "Sold", "Scrapped", "Capitalized")
    summary["can"] = {
        "write": can_write,
        "scrap": can_write and doc.docstatus == 1 and not_disposed
        and bool(frappe.has_permission("Journal Entry", "submit")),
        "restore": can_write and bool(doc.journal_entry_for_scrap)
        and bool(frappe.has_permission("Journal Entry", "cancel")),
        # These mirror the server-side checks in movements.create / maintenance.create_repair /
        # maintenance.create_plan: Asset write plus create on the target doctype (plans also need team read). The UI uses
        # them only to decide what to show; the real enforcement stays in those endpoints.
        "create_movement": can_write and not_disposed and bool(frappe.has_permission("Asset Movement", "create")),
        "create_repair": can_write and not_disposed and bool(frappe.has_permission("Asset Repair", "create")),
        "create_maintenance_plan": can_write and not_disposed
        and bool(frappe.has_permission("Asset Maintenance", "create"))
        and bool(frappe.has_permission("Asset Maintenance Team", "read")),
    }
    return summary


@frappe.whitelist(methods=["POST"])
def scrap(name: str, scrap_date: str | None = None):
    """Scrap an asset using ERPNext's own logic (journal entry included)."""
    from erpnext.assets.doctype.asset.depreciation import scrap_asset

    require_csrf_token()
    get_asset(name, "write")
    if not frappe.has_permission("Journal Entry", "submit"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Journal Entry submit", frappe.PermissionError)
    try:
        parsed = getdate(scrap_date) if scrap_date else None
    except Exception:
        frappe.throw(f"{ErrorCode.INVALID}: scrap_date", frappe.ValidationError)
    scrap_asset(name, parsed)
    return get_summary(name)


@frappe.whitelist(methods=["POST"])
def restore(name: str):
    from erpnext.assets.doctype.asset.depreciation import restore_asset

    require_csrf_token()
    doc = get_asset(name, "write")
    if doc.journal_entry_for_scrap and not frappe.has_permission("Journal Entry", "cancel"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Journal Entry cancel", frappe.PermissionError)
    restore_asset(name)
    return get_summary(name)


@frappe.whitelist(methods=["POST"])
def create(asset_name: str, item_code: str, company: str, location: str, purchase_date: str,
           available_for_use_date: str, net_purchase_amount: float, custodian: str | None = None):
    """Create and submit an Existing Asset. Field-level rules (item/category match, dates,
    cost center, …) are enforced by ERPNext's own Asset.validate(); we only pre-check what
    produces a clearer message than the core one and what core cannot check (permissions)."""
    require_csrf_token()
    if not frappe.has_permission("Asset", "create"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset create", frappe.PermissionError)
    if not frappe.has_permission("Company", "read", company):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Company {company}", frappe.PermissionError)
    if not frappe.has_permission("Location", "read", location):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Location {location}", frappe.PermissionError)
    if not frappe.has_permission("Asset Movement", "create"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Movement create", frappe.PermissionError)

    asset_name = (asset_name or "").strip()
    if not asset_name or len(asset_name) > 140:
        frappe.throw(f"{ErrorCode.INVALID}: asset_name", frappe.ValidationError)
    if flt(net_purchase_amount) <= 0:
        frappe.throw(f"{ErrorCode.INVALID}: net_purchase_amount must be positive", frappe.ValidationError)
    try:
        p_date, u_date = getdate(purchase_date), getdate(available_for_use_date)
    except Exception:
        frappe.throw(f"{ErrorCode.INVALID}: purchase_date or available_for_use_date", frappe.ValidationError)
    if p_date > getdate():
        frappe.throw(f"{ErrorCode.INVALID}: purchase_date is in the future", frappe.ValidationError)
    if u_date < p_date:
        # ERPNext's own check for this is skipped for "Existing Asset" (see Asset.validate_asset_values);
        # an asset cannot be in use before it was purchased, so we enforce it ourselves.
        frappe.throw(f"{ErrorCode.INVALID}: available_for_use_date is before purchase_date", frappe.ValidationError)

    item = frappe.db.get_value("Item", item_code, ["is_fixed_asset", "disabled", "asset_category"], as_dict=True)
    if not item or not item.is_fixed_asset or item.disabled:
        frappe.throw(f"{ErrorCode.INVALID}: item_code", frappe.ValidationError)

    doc = frappe.get_doc({
        "doctype": "Asset", "asset_name": asset_name, "item_code": item_code,
        "asset_category": item.asset_category, "company": company, "location": location,
        "custodian": custodian or None, "asset_type": "Existing Asset",
        "purchase_date": p_date, "available_for_use_date": u_date,
        "net_purchase_amount": flt(net_purchase_amount), "asset_quantity": 1,
        "calculate_depreciation": 0,
    })
    doc.insert()
    doc.submit()
    return get_summary(doc.name)
