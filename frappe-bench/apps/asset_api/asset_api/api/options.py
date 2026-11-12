import frappe


@frappe.whitelist()
def new_asset_form():
    """Dropdown data for the new-asset form, already scoped to the caller's permissions."""
    if not frappe.has_permission("Asset", "create"):
        frappe.throw("ASSET_API_FORBIDDEN: Asset create", frappe.PermissionError)
    return {
        "companies": frappe.get_list("Company", fields=["name"], order_by="name", limit=0),
        "categories": frappe.get_list("Asset Category", fields=["name"], order_by="name", limit=0),
        "locations": frappe.get_list("Location", filters={"is_group": 0}, fields=["name"],
                                     order_by="name", limit=0),
        "items": frappe.get_list("Item", filters={"is_fixed_asset": 1, "disabled": 0},
                                 fields=["name as item_code", "item_name", "asset_category"],
                                 order_by="item_name", limit=0),
    }
