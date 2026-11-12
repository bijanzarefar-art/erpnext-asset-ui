import frappe


@frappe.whitelist()
def dashboard():
    """Counts and book value per status, aggregated server-side under the caller's permissions."""
    rows = frappe.get_list(
        "Asset",
        fields=["status", {"COUNT": "*", "as": "count"}, {"SUM": "value_after_depreciation", "as": "value"}],
        group_by="status",
        limit=0,
    )
    return {
        "by_status": rows,
        "total_count": sum(r["count"] or 0 for r in rows),
        "total_value": sum(r["value"] or 0 for r in rows),
    }
