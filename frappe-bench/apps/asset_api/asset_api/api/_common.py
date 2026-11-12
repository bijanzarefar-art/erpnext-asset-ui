"""Shared helpers: error codes and permission checks for the asset_api endpoints."""

import frappe


class ErrorCode:
    FORBIDDEN = "ASSET_API_FORBIDDEN"
    NOT_FOUND = "ASSET_API_NOT_FOUND"
    INVALID = "ASSET_API_INVALID"


def forbid(message: str):
    frappe.throw(f"{ErrorCode.FORBIDDEN}: {message}", frappe.PermissionError)


def get_asset(name: str, ptype: str = "read"):
    """Load an Asset and check the permission on the loaded document."""
    if not name or not frappe.db.exists("Asset", name):
        frappe.throw(f"{ErrorCode.NOT_FOUND}: Asset {name}", frappe.DoesNotExistError)
    doc = frappe.get_doc("Asset", name)
    if not frappe.has_permission("Asset", ptype, doc=doc):
        forbid(f"No {ptype} permission on Asset {name}")
    return doc


def require_csrf_token():
    """Writes must come from a session that has a saved CSRF token.

    Frappe skips its CSRF check when the session has no saved token (sessions made by
    /api/method/login), so a write from such a session would pass unprotected. Real HTTP
    requests without a saved token are refused here; session.me creates the token."""
    if frappe.request and not frappe.session.data.get("csrf_token"):
        frappe.throw("Invalid Request", frappe.CSRFTokenError)
