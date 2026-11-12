"""Test fixtures for asset_api, so the suite runs on any site whose setup wizard is complete.

Every helper is idempotent: on a site that already has the records nothing is created.
Records made here live inside the test transaction and are rolled back with each test class."""

import frappe

LOCATIONS = ("دفتر مرکزی", "انبار تهران")
CATEGORY = "تجهیزات اداری"
ITEM = "ASSET-DESK"
TEST_USER = "asset.ui.test@example.com"
NOROLE_USER = "asset.ui.norole@example.com"
TEST_USER_ROLES = ("Accounts User", "Accounts Manager", "Stock User", "Manufacturing User")


def default_company() -> str:
    company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
    if not company:
        raise RuntimeError("asset_api tests need a Company: finish the setup wizard first")
    return company


def _account(company: str, account_type: str) -> str | None:
    return frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_type": account_type}, "name")


def ensure_fixtures() -> str:
    """Create the master data and users the tests rely on. Returns the company name."""
    frappe.set_user("Administrator")
    company = default_company()

    for loc in LOCATIONS:
        if not frappe.db.exists("Location", loc):
            frappe.get_doc({"doctype": "Location", "location_name": loc}).insert()

    if not frappe.db.exists("Asset Category", CATEGORY):
        frappe.get_doc({
            "doctype": "Asset Category", "asset_category_name": CATEGORY,
            "accounts": [{
                "company_name": company,
                "fixed_asset_account": _account(company, "Fixed Asset"),
                "accumulated_depreciation_account": _account(company, "Accumulated Depreciation"),
                "depreciation_expense_account": _account(company, "Depreciation"),
                "capital_work_in_progress_account": _account(company, "Capital Work in Progress"),
            }],
        }).insert()

    if not frappe.db.exists("Item", ITEM):
        frappe.get_doc({
            "doctype": "Item", "item_code": ITEM, "item_name": "میز اداری",
            "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
            "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": CATEGORY, "stock_uom": "Nos",
        }).insert()

    ensure_user(TEST_USER, "Asset UI Test", TEST_USER_ROLES)
    ensure_user(NOROLE_USER, "Asset UI NoRole", ())
    return company


def ensure_user(email: str, first_name: str, roles: tuple[str, ...]):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name,
                        "send_welcome_email": 0, "enabled": 1}).insert()
    user = frappe.get_doc("User", email)
    missing = [r for r in roles if r not in {x.role for x in user.roles} and frappe.db.exists("Role", r)]
    if missing:
        user.add_roles(*missing)
