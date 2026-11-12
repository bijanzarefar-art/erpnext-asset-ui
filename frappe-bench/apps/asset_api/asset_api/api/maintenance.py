import frappe
from frappe.utils import get_datetime, getdate, now_datetime

from asset_api.api._common import ErrorCode, get_asset, require_csrf_token

REPAIR_FIELDS = ["name", "failure_date", "completion_date", "repair_status", "description",
                 "actions_performed", "repair_cost", "total_repair_cost", "docstatus"]
LOG_FIELDS = ["name", "task_name", "maintenance_type", "periodicity", "due_date", "completion_date",
              "maintenance_status", "actions_performed", "docstatus"]

PERIODICITIES = ("Daily", "Weekly", "Monthly", "Quarterly", "Half-yearly", "Yearly", "2 Yearly", "3 Yearly")
MAINTENANCE_TYPES = ("Preventive Maintenance", "Calibration")
MAX_TASKS = 20


def _invalid(what: str):
    frappe.throw(f"{ErrorCode.INVALID}: {what}", frappe.ValidationError)


def _dt(value, field):
    try:
        return get_datetime(value)
    except Exception:
        _invalid(field)


@frappe.whitelist()
def list_repairs(asset: str):
    get_asset(asset, "read")
    if not frappe.has_permission("Asset Repair", "read"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Repair read", frappe.PermissionError)
    return frappe.get_list("Asset Repair", filters={"asset": asset, "docstatus": ["<", 2]},
                           fields=REPAIR_FIELDS, order_by="failure_date desc", limit=100)


@frappe.whitelist(methods=["POST"])
def create_repair(asset: str, failure_date: str, description: str):
    """Open a repair (status Pending, saved as draft). It is completed and submitted later."""
    require_csrf_token()
    doc = get_asset(asset, "write")
    if doc.docstatus != 1 or doc.status in ("Scrapped", "Sold", "Cancelled", "Capitalized"):
        _invalid("asset is not repairable")
    description = (description or "").strip()
    if not description or len(description) > 2000:
        _invalid("description")
    failure = _dt(failure_date, "failure_date")
    if failure > now_datetime():
        _invalid("failure_date is in the future")
    if not frappe.has_permission("Asset Repair", "create"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Repair create", frappe.PermissionError)
    repair = frappe.get_doc({"doctype": "Asset Repair", "asset": asset, "company": doc.company,
                             "failure_date": failure, "repair_status": "Pending",
                             "description": description}).insert()
    return {f: repair.get(f) for f in REPAIR_FIELDS}


@frappe.whitelist(methods=["POST"])
def complete_repair(name: str, completion_date: str, actions_performed: str):
    """Mark a Pending repair Completed and submit it.

    No cost parameter on purpose: ERPNext derives repair cost from linked Purchase Invoices and
    consumed stock items and overwrites any value typed here."""
    require_csrf_token()
    if not frappe.db.exists("Asset Repair", name):
        frappe.throw(f"{ErrorCode.NOT_FOUND}: Asset Repair {name}", frappe.DoesNotExistError)
    repair = frappe.get_doc("Asset Repair", name)
    if not frappe.has_permission("Asset Repair", "submit", doc=repair):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Repair submit", frappe.PermissionError)
    get_asset(repair.asset, "write")
    if repair.docstatus != 0 or repair.repair_status != "Pending":
        _invalid("repair is not pending")
    done = _dt(completion_date, "completion_date")
    if done < get_datetime(repair.failure_date) or done > now_datetime():
        _invalid("completion_date")
    actions = (actions_performed or "").strip()
    if not actions or len(actions) > 2000:
        _invalid("actions_performed")
    repair.update({"repair_status": "Completed", "completion_date": done,
                   "actions_performed": actions})
    repair.save()
    repair.submit()
    return {f: repair.get(f) for f in REPAIR_FIELDS}


@frappe.whitelist()
def list_logs(asset: str):
    """Maintenance logs (planned, overdue, completed) of an asset."""
    get_asset(asset, "read")
    if not frappe.has_permission("Asset Maintenance Log", "read"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance Log read", frappe.PermissionError)
    names = frappe.get_all("Asset Maintenance", filters={"asset_name": asset}, pluck="name")
    if not names:
        return []
    return frappe.get_list("Asset Maintenance Log",
                           filters={"asset_maintenance": ["in", names], "docstatus": ["<", 2]},
                           fields=LOG_FIELDS, order_by="due_date desc", limit=100)


@frappe.whitelist(methods=["POST"])
def complete_log(name: str, completion_date: str, actions_performed: str):
    """Complete a Planned or Overdue maintenance log and submit it."""
    require_csrf_token()
    if not frappe.db.exists("Asset Maintenance Log", name):
        frappe.throw(f"{ErrorCode.NOT_FOUND}: Asset Maintenance Log {name}", frappe.DoesNotExistError)
    log = frappe.get_doc("Asset Maintenance Log", name)
    if not frappe.has_permission("Asset Maintenance Log", "submit", doc=log):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance Log submit", frappe.PermissionError)
    asset = frappe.db.get_value("Asset Maintenance", log.asset_maintenance, "asset_name")
    get_asset(asset, "write")
    if log.docstatus != 0 or log.maintenance_status not in ("Planned", "Overdue"):
        _invalid("log is not open")
    try:
        done = getdate(completion_date)
    except Exception:
        _invalid("completion_date")
    if done > getdate():
        _invalid("completion_date is in the future")
    actions = (actions_performed or "").strip()
    if not actions or len(actions) > 2000:
        _invalid("actions_performed")
    log.update({"maintenance_status": "Completed", "completion_date": done, "actions_performed": actions})
    log.save()
    log.submit()
    return {f: log.get(f) for f in LOG_FIELDS}


@frappe.whitelist()
def get_plan(asset: str):
    """The asset's maintenance plan (team + tasks), or None if it has no plan yet."""
    get_asset(asset, "read")
    if not frappe.has_permission("Asset Maintenance", "read"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance read", frappe.PermissionError)
    if not frappe.db.exists("Asset Maintenance", asset):
        return None
    plan = frappe.get_doc("Asset Maintenance", asset)
    return {
        "name": plan.name,
        "maintenance_team": plan.maintenance_team,
        "tasks": [{"maintenance_task": t.maintenance_task, "maintenance_type": t.maintenance_type,
                   "periodicity": t.periodicity, "next_due_date": t.next_due_date,
                   "maintenance_status": t.maintenance_status, "assign_to": t.assign_to}
                  for t in plan.asset_maintenance_tasks],
    }


@frappe.whitelist()
def list_teams():
    """Maintenance teams the caller may read, each with its member list (for the assign_to picker)."""
    if not frappe.has_permission("Asset Maintenance Team", "read"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance Team read", frappe.PermissionError)
    teams = frappe.get_list("Asset Maintenance Team", fields=["name", "maintenance_team_name", "company"],
                            order_by="maintenance_team_name", limit=100)
    for t in teams:
        t["members"] = frappe.get_all("Maintenance Team Member", filters={"parent": t["name"]},
                                      fields=["team_member", "full_name"], order_by="idx")
    return teams


@frappe.whitelist(methods=["POST"])
def create_plan(asset: str, maintenance_team: str, tasks: list[dict]):
    """Create an Asset Maintenance plan with one or more tasks (Asset Maintenance is not submittable;
    insert() makes it active). Requires write on the Asset, like every other change to an asset.

    Each task dict: maintenance_task, maintenance_type, periodicity, start_date, assign_to.
    ERPNext's own Asset Maintenance.validate() generates next_due_date and the first log rows;
    it also re-checks that each assignee is a team member, so our pre-check is only for a clearer
    message, not the real guard."""
    require_csrf_token()
    doc = get_asset(asset, "write")
    if doc.docstatus != 1:
        _invalid("asset must be submitted")
    if not frappe.has_permission("Asset Maintenance", "create"):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance create", frappe.PermissionError)
    if not frappe.has_permission("Asset Maintenance Team", "read", maintenance_team):
        frappe.throw(f"{ErrorCode.FORBIDDEN}: Asset Maintenance Team {maintenance_team}", frappe.PermissionError)
    if frappe.db.exists("Asset Maintenance", asset):
        _invalid("asset already has a maintenance plan")

    tasks = tasks or []
    if not 1 <= len(tasks) <= MAX_TASKS:
        _invalid(f"tasks must contain 1 to {MAX_TASKS} items")

    members = set(frappe.get_all("Maintenance Team Member", filters={"parent": maintenance_team}, pluck="team_member"))
    rows = []
    for i, t in enumerate(tasks):
        name = (t.get("maintenance_task") or "").strip()
        if not name or len(name) > 140:
            _invalid(f"tasks[{i}].maintenance_task")
        if t.get("maintenance_type") not in MAINTENANCE_TYPES:
            _invalid(f"tasks[{i}].maintenance_type")
        if t.get("periodicity") not in PERIODICITIES:
            _invalid(f"tasks[{i}].periodicity")
        try:
            start = getdate(t.get("start_date"))
        except Exception:
            _invalid(f"tasks[{i}].start_date")
        assign_to = t.get("assign_to")
        if not assign_to or assign_to not in members:
            _invalid(f"tasks[{i}].assign_to must be a member of the team")
        rows.append({
            "maintenance_task": name, "maintenance_type": t["maintenance_type"],
            "periodicity": t["periodicity"], "start_date": start, "assign_to": assign_to,
            "maintenance_status": "Planned",
        })

    item_code, item_name, asset_category = frappe.db.get_value(
        "Asset", asset, ["item_code", "item_name", "asset_category"])
    plan = frappe.get_doc({
        "doctype": "Asset Maintenance", "asset_name": asset, "item_code": item_code,
        "item_name": item_name, "asset_category": asset_category, "company": doc.company,
        "maintenance_team": maintenance_team, "asset_maintenance_tasks": rows,
    })
    plan.insert()
    return {"name": plan.name, "task_count": len(plan.asset_maintenance_tasks)}
