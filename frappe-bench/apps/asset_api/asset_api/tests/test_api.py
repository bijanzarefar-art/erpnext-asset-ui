import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from asset_api.api import _common, assets, maintenance, movements, reports, session
from asset_api.tests import fixtures
from asset_api.tests.fixtures import NOROLE_USER, TEST_USER

COMPANY = None  # set from the site in AssetApiTestCase.setUpClass


class AssetApiTestCase(IntegrationTestCase):
    """Creates the master data and users the tests need, so the suite runs on a fresh site."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        global COMPANY
        COMPANY = fixtures.ensure_fixtures()


def make_asset(name="API Test Asset"):
    a = frappe.get_doc({
        "doctype": "Asset", "asset_name": name, "item_code": "ASSET-DESK",
        "asset_category": "تجهیزات اداری", "company": COMPANY, "location": "دفتر مرکزی",
        "asset_type": "Existing Asset", "purchase_date": add_days(nowdate(), -90),
        "available_for_use_date": add_days(nowdate(), -80), "net_purchase_amount": 1000000,
        "asset_quantity": 1, "calculate_depreciation": 0,
    }).insert()
    a.submit()
    return a


class TestSession(AssetApiTestCase):
    def test_guest_gets_no_identity_or_token(self):
        frappe.set_user("Guest")
        self.assertEqual(session.me(), {"user": None})

    def test_logged_in_user_gets_csrf_token(self):
        frappe.set_user(TEST_USER)
        data = session.me()
        self.assertEqual(data["user"], TEST_USER)
        self.assertTrue(data["csrf_token"])
        self.assertTrue(data["can"]["read"])

    def test_token_is_stable_within_a_session(self):
        frappe.set_user(TEST_USER)
        self.assertEqual(session.me()["csrf_token"], session.me()["csrf_token"])

    FEATURE_KEYS = ("asset_list", "asset_create", "asset_movement", "asset_repair",
                    "maintenance_plan", "maintenance_team")

    def test_features_present_for_privileged_user(self):
        frappe.set_user(TEST_USER)
        features = session.me()["features"]
        self.assertEqual(set(features), set(self.FEATURE_KEYS))
        for key in self.FEATURE_KEYS:
            self.assertTrue(features[key], key)

    def test_features_false_for_user_without_roles(self):
        frappe.set_user(NOROLE_USER)
        features = session.me()["features"]
        for key in self.FEATURE_KEYS:
            self.assertFalse(features[key], key)

    def test_guest_has_no_features(self):
        frappe.set_user("Guest")
        self.assertNotIn("features", session.me())

    def tearDown(self):
        frappe.set_user("Administrator")


class TestAssets(AssetApiTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = make_asset()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_summary_has_core_fields_and_flags(self):
        s = assets.get_summary(self.asset.name)
        self.assertEqual(s["asset_name"], "API Test Asset")
        self.assertEqual(s["net_purchase_amount"], 1000000)
        self.assertTrue(s["can"]["scrap"])
        self.assertFalse(s["can"]["restore"])
        self.assertEqual(s["depreciation_schedule"], [])
        self.assertTrue(s["can"]["create_movement"])
        self.assertTrue(s["can"]["create_repair"])
        self.assertTrue(s["can"]["create_maintenance_plan"])

    def test_summary_flags_false_after_scrap(self):
        assets.scrap(self.asset.name)
        s = assets.get_summary(self.asset.name)
        self.assertFalse(s["can"]["scrap"])
        self.assertFalse(s["can"]["create_movement"])
        self.assertFalse(s["can"]["create_repair"])
        self.assertFalse(s["can"]["create_maintenance_plan"])
        self.assertTrue(s["can"]["restore"])

    def test_summary_missing_asset_is_not_found(self):
        with self.assertRaises(frappe.DoesNotExistError):
            assets.get_summary("NO-SUCH-ASSET")

    def test_user_without_roles_is_forbidden(self):
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            assets.get_summary(self.asset.name)
        with self.assertRaises(frappe.PermissionError):
            assets.scrap(self.asset.name)

    def test_scrap_then_restore(self):
        s = assets.scrap(self.asset.name)
        self.assertEqual(s["status"], "Scrapped")
        self.assertTrue(s["can"]["restore"])
        r = assets.restore(self.asset.name)
        self.assertNotEqual(r["status"], "Scrapped")
        self.assertFalse(r["can"]["restore"])

    def test_movement_transfers_location(self):
        out = movements.create([self.asset.name], "Transfer", target_location="انبار تهران")
        self.assertEqual(out["docstatus"], 1)
        self.assertEqual(frappe.db.get_value("Asset", self.asset.name, "location"), "انبار تهران")

    def test_movement_rejects_too_many_and_missing_target(self):
        with self.assertRaises(frappe.ValidationError):
            movements.create([f"X{i}" for i in range(51)], "Transfer", target_location="انبار تهران")
        with self.assertRaises(frappe.ValidationError):
            movements.create([self.asset.name], "Transfer")

    def test_movement_deduplicates_assets(self):
        out = movements.create([self.asset.name, self.asset.name], "Transfer", target_location="انبار تهران")
        self.assertEqual(frappe.db.count("Asset Movement Item", {"parent": out["name"]}), 1)

    def test_scrap_rejects_malformed_date(self):
        with self.assertRaises(frappe.ValidationError):
            assets.scrap(self.asset.name, "not-a-date")

    def test_movement_rejects_bad_purpose(self):
        with self.assertRaises(frappe.ValidationError):
            movements.create([self.asset.name], "Nonsense")

    def test_movement_forbidden_without_roles(self):
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            movements.create([self.asset.name], "Transfer", target_location="انبار تهران")

    def test_dashboard_counts_new_asset(self):
        before = reports.dashboard()
        make_asset("API Test Asset 2")
        after = reports.dashboard()
        self.assertEqual(after["total_count"], before["total_count"] + 1)
        self.assertEqual(after["total_value"], before["total_value"] + 1000000)

    def test_dashboard_for_user_without_roles_fails(self):
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            reports.dashboard()


class TestCsrfGate(AssetApiTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def test_write_without_saved_token_is_refused_on_http(self):
        frappe.set_user(TEST_USER)
        frappe.local.session.data.csrf_token = None
        frappe.local.request = frappe._dict(method="POST")
        try:
            with self.assertRaises(frappe.CSRFTokenError):
                _common.require_csrf_token()
            frappe.local.session.data.csrf_token = "abc"
            _common.require_csrf_token()  # passes once a token is saved
        finally:
            frappe.local.request = None


class TestLocationScoping(AssetApiTestCase):
    """Visibility by Location uses Frappe's built-in User Permission; no custom query hooks."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.a_hq = make_asset("Scope HQ")
        self.a_wh = make_asset("Scope WH")
        frappe.db.set_value("Asset", self.a_wh.name, "location", "انبار تهران")
        # Test classes roll back once per class, so make this idempotent across test methods
        if not frappe.db.exists("User Permission", {"user": TEST_USER, "allow": "Location", "for_value": "دفتر مرکزی"}):
            frappe.get_doc({"doctype": "User Permission", "user": TEST_USER, "allow": "Location",
                            "for_value": "دفتر مرکزی", "apply_to_all_doctypes": 1}).insert()
        frappe.clear_cache(user=TEST_USER)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_list_and_dashboard_only_show_allowed_location(self):
        frappe.set_user(TEST_USER)
        names = {r["name"] for r in frappe.get_list("Asset", fields=["name"], limit=0)}
        self.assertIn(self.a_hq.name, names)
        self.assertNotIn(self.a_wh.name, names)
        total = reports.dashboard()["total_count"]
        self.assertEqual(total, len(names))

    def test_summary_of_hidden_asset_is_forbidden(self):
        frappe.set_user(TEST_USER)
        with self.assertRaises(frappe.PermissionError):
            assets.get_summary(self.a_wh.name)
        self.assertEqual(assets.get_summary(self.a_hq.name)["name"], self.a_hq.name)

    def test_cannot_move_into_hidden_location(self):
        frappe.set_user(TEST_USER)
        with self.assertRaises(frappe.PermissionError):
            movements.create([self.a_hq.name], "Transfer", target_location="انبار تهران")


class TestMaintenance(AssetApiTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = make_asset("Maint Asset")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_repair_lifecycle(self):
        from asset_api.api import maintenance
        r = maintenance.create_repair(self.asset.name, add_days(nowdate(), -2) + " 09:00:00", "موتور خراب است")
        self.assertEqual((r["repair_status"], r["docstatus"]), ("Pending", 0))
        done = maintenance.complete_repair(r["name"], add_days(nowdate(), -1) + " 12:00:00", "موتور تعویض شد")
        self.assertEqual((done["repair_status"], done["docstatus"]), ("Completed", 1))
        listed = maintenance.list_repairs(self.asset.name)
        self.assertEqual([x["name"] for x in listed], [r["name"]])

    def test_repair_validation(self):
        from asset_api.api import maintenance
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_repair(self.asset.name, "2999-01-01 00:00:00", "x")
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_repair(self.asset.name, "garbage", "x")
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_repair(self.asset.name, add_days(nowdate(), -1) + " 09:00:00", "  ")
        r = maintenance.create_repair(self.asset.name, add_days(nowdate(), -2) + " 09:00:00", "x")
        with self.assertRaises(frappe.ValidationError):  # completion before failure
            maintenance.complete_repair(r["name"], add_days(nowdate(), -3) + " 09:00:00", "x")

    def test_repair_forbidden_without_roles(self):
        from asset_api.api import maintenance
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            maintenance.create_repair(self.asset.name, add_days(nowdate(), -1) + " 09:00:00", "x")
        with self.assertRaises(frappe.PermissionError):
            maintenance.list_repairs(self.asset.name)

    def test_logs_empty_without_plan_and_missing_log(self):
        from asset_api.api import maintenance
        self.assertEqual(maintenance.list_logs(self.asset.name), [])
        with self.assertRaises(frappe.DoesNotExistError):
            maintenance.complete_log("NO-SUCH-LOG", nowdate(), "x")


class TestMaintenanceLogs(AssetApiTestCase):
    def setUp(self):
        from asset_api.api import maintenance
        self.m = maintenance
        frappe.set_user("Administrator")
        self.asset = make_asset("Log Asset")
        team = "تیم تست لاگ"
        if not frappe.db.exists("Asset Maintenance Team", team):
            frappe.get_doc({"doctype": "Asset Maintenance Team", "maintenance_team_name": team, "company": COMPANY,
                            "maintenance_manager": TEST_USER,
                            "maintenance_team_members": [{"team_member": TEST_USER, "maintenance_role": "Manufacturing User"}]}).insert()
        frappe.get_doc({"doctype": "Asset Maintenance", "asset_name": self.asset.name, "company": COMPANY,
                        "maintenance_team": team, "asset_maintenance_tasks": [
                            {"maintenance_task": "بازرسی", "maintenance_type": "Preventive Maintenance",
                             "periodicity": "Monthly", "start_date": add_days(nowdate(), -45),
                             "assign_to": TEST_USER, "maintenance_status": "Planned"}]}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_list_and_complete_overdue_log(self):
        logs = self.m.list_logs(self.asset.name)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["maintenance_status"], "Overdue")
        done = self.m.complete_log(logs[0]["name"], nowdate(), "بازرسی انجام شد")
        self.assertEqual((done["maintenance_status"], done["docstatus"]), ("Completed", 1))
        with self.assertRaises(frappe.ValidationError):  # already completed
            self.m.complete_log(logs[0]["name"], nowdate(), "دوباره")

    def test_complete_log_validation(self):
        name = self.m.list_logs(self.asset.name)[0]["name"]
        with self.assertRaises(frappe.ValidationError):
            self.m.complete_log(name, add_days(nowdate(), 3), "آینده")
        with self.assertRaises(frappe.ValidationError):
            self.m.complete_log(name, "garbage", "x")
        with self.assertRaises(frappe.ValidationError):
            self.m.complete_log(name, nowdate(), "   ")

    def test_user_without_roles_cannot_see_or_complete(self):
        name = self.m.list_logs(self.asset.name)[0]["name"]
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            self.m.list_logs(self.asset.name)
        with self.assertRaises(frappe.PermissionError):
            self.m.complete_log(name, nowdate(), "x")


class TestCreateAsset(AssetApiTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def valid_args(self, **override):
        args = dict(asset_name="New API Asset", item_code="ASSET-DESK", company=COMPANY,
                    location="دفتر مرکزی", purchase_date=add_days(nowdate(), -5),
                    available_for_use_date=nowdate(), net_purchase_amount=2500000)
        args.update(override)
        return args

    def test_create_submits_and_is_readable(self):
        out = assets.create(**self.valid_args())
        self.assertEqual(out["status"], "Submitted")
        self.assertEqual(out["net_purchase_amount"], 2500000)
        self.assertEqual(frappe.db.get_value("Asset", out["name"], "docstatus"), 1)

    def test_create_rejects_bad_input(self):
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(asset_name="  "))
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(net_purchase_amount=0))
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(net_purchase_amount=-10))
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(purchase_date="2999-01-01"))
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(item_code="NO-SUCH-ITEM"))

    def test_create_lets_core_validation_through(self):
        # available_for_use_date before purchase_date: ERPNext's own rule, not ours
        with self.assertRaises(frappe.ValidationError):
            assets.create(**self.valid_args(
                purchase_date=nowdate(), available_for_use_date=add_days(nowdate(), -10)))

    def test_create_forbidden_without_roles(self):
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            assets.create(**self.valid_args())

    def test_options_endpoint(self):
        from asset_api.api import options
        data = options.new_asset_form()
        for key in ("companies", "categories", "locations", "items"):
            self.assertIn(key, data)
        self.assertTrue(any(c["name"] == COMPANY for c in data["companies"]))

    def test_options_forbidden_without_create(self):
        from asset_api.api import options
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            options.new_asset_form()


class TestCreatePlan(AssetApiTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = make_asset("Plan API Asset")
        self.team = "تیم تست ساخت برنامه"
        if not frappe.db.exists("Asset Maintenance Team", self.team):
            frappe.get_doc({"doctype": "Asset Maintenance Team", "maintenance_team_name": self.team,
                            "company": COMPANY, "maintenance_manager": TEST_USER,
                            "maintenance_team_members": [
                                {"team_member": TEST_USER, "maintenance_role": "Manufacturing User"}]}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")

    def valid_task(self, **override):
        task = dict(maintenance_task="بازرسی دوره‌ای", maintenance_type="Preventive Maintenance",
                   periodicity="Monthly", start_date=add_days(nowdate(), -10), assign_to=TEST_USER)
        task.update(override)
        return task

    def test_create_plan_and_list_teams(self):
        teams = maintenance.list_teams()
        self.assertTrue(any(t["name"] == self.team for t in teams))
        found = next(t for t in teams if t["name"] == self.team)
        self.assertEqual([m["team_member"] for m in found["members"]], [TEST_USER])

        out = maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])
        self.assertEqual(out["task_count"], 1)
        self.assertTrue(frappe.db.exists("Asset Maintenance", self.asset.name))
        logs = maintenance.list_logs(self.asset.name)
        self.assertEqual(len(logs), 1)

    def test_create_plan_rejects_duplicate(self):
        maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])

    def test_create_plan_rejects_bad_task_fields(self):
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [])
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task(maintenance_task="  ")])
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task(periodicity="Hourly")])
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task(maintenance_type="Repair")])
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task(start_date="garbage")])

    def test_create_plan_rejects_non_member_assignee(self):
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task(assign_to=NOROLE_USER)])

    def test_create_plan_forbidden_without_roles(self):
        frappe.set_user(NOROLE_USER)
        with self.assertRaises(frappe.PermissionError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])
        with self.assertRaises(frappe.PermissionError):
            maintenance.list_teams()

    def test_create_plan_needs_write_on_asset(self):
        # Manufacturing User can create Asset Maintenance but has no Asset permission; a read-only
        # share on the asset must not be enough to attach a maintenance plan to it.
        email = "asset.ui.readonly@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "Read Only",
                            "send_welcome_email": 0, "roles": [{"role": "Manufacturing User"}]}).insert()
        frappe.share.add("Asset", self.asset.name, email, read=1, write=0, notify=0)
        frappe.set_user(email)
        self.assertTrue(frappe.has_permission("Asset", "read", doc=self.asset.name))
        self.assertTrue(frappe.has_permission("Asset Maintenance", "create"))
        with self.assertRaises(frappe.PermissionError):
            maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])

    def test_get_plan_none_then_populated(self):
        self.assertIsNone(maintenance.get_plan(self.asset.name))
        maintenance.create_plan(self.asset.name, self.team, [self.valid_task()])
        plan = maintenance.get_plan(self.asset.name)
        self.assertEqual(plan["maintenance_team"], self.team)
        self.assertEqual(len(plan["tasks"]), 1)


class TestFeatureFlagsMatchServer(AssetApiTestCase):
    """Each UI flag must be true only when the endpoint it opens accepts the request."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = make_asset("Flag Asset")

    def tearDown(self):
        frappe.set_user("Administrator")

    def features_for(self, email, *roles):
        fixtures.ensure_user(email, "Flag Test", roles)
        frappe.clear_cache(user=email)
        frappe.set_user(email)
        return session.me()["features"]

    def test_accounts_user_alone_cannot_create_or_move(self):
        feats = self.features_for("asset.flag.accounts@example.com", "Accounts User")
        self.assertFalse(feats["asset_create"])
        self.assertFalse(feats["asset_movement"])
        self.assertTrue(feats["asset_repair"])
        self.assertFalse(feats["maintenance_plan"])
        with self.assertRaises(frappe.PermissionError):
            assets.create(asset_name="Flag new", item_code=fixtures.ITEM, company=COMPANY,
                          location="دفتر مرکزی", purchase_date=add_days(nowdate(), -5),
                          available_for_use_date=nowdate(), net_purchase_amount=2500000)

    def test_stock_manager_cannot_move_without_asset_write(self):
        feats = self.features_for("asset.flag.stock@example.com", "Stock Manager")
        self.assertFalse(feats["asset_movement"])
        self.assertFalse(feats["asset_create"])
        with self.assertRaises(frappe.PermissionError):
            movements.create([self.asset.name], "Transfer", target_location="انبار تهران")

    def test_manufacturing_user_cannot_repair_without_asset_write(self):
        feats = self.features_for("asset.flag.mfg@example.com", "Manufacturing User")
        self.assertFalse(feats["asset_repair"])
        self.assertFalse(feats["maintenance_plan"])
        self.assertTrue(feats["maintenance_team"])
        with self.assertRaises(frappe.PermissionError):
            maintenance.create_repair(self.asset.name, add_days(nowdate(), -1) + " 09:00:00", "x")

    def test_quality_manager_has_no_plan_without_team_access(self):
        feats = self.features_for("asset.flag.quality@example.com", "Quality Manager")
        self.assertFalse(feats["maintenance_plan"])
        self.assertFalse(feats["maintenance_team"])

    def test_accounts_and_stock_manager_can_create_and_move(self):
        feats = self.features_for("asset.flag.both@example.com", "Accounts User", "Stock Manager")
        self.assertTrue(feats["asset_create"])
        self.assertTrue(feats["asset_movement"])


class TestScrapPermissions(AssetApiTestCase):
    """ERPNext's scrap_asset needs Journal Entry submit; restore cancels that entry."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = make_asset("Scrap Perm Asset")

    def tearDown(self):
        frappe.set_user("Administrator")

    def user_without_journal_entry(self, email):
        """Can write assets and read the warehouse location, but has no Journal Entry permission."""
        fixtures.ensure_user(email, "Scrap Test", ("Manufacturing User",))
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Location", "for_value": "دفتر مرکزی"}):
            frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Location",
                            "for_value": "دفتر مرکزی", "apply_to_all_doctypes": 1}).insert()
        frappe.share.add("Asset", self.asset.name, email, read=1, write=1, notify=0)
        frappe.clear_cache(user=email)
        return email

    def test_scrap_flag_and_restore_flag_follow_journal_entry_rights(self):
        email = self.user_without_journal_entry("asset.scrap.noje@example.com")
        frappe.set_user(email)
        summary = assets.get_summary(self.asset.name)
        self.assertFalse(summary["can"]["scrap"],
                         "no Journal Entry submit: the scrap button must be hidden")
        with self.assertRaises(frappe.PermissionError):
            assets.scrap(self.asset.name)

    def test_restore_flag_false_without_journal_entry_cancel(self):
        assets.scrap(self.asset.name)
        email = self.user_without_journal_entry("asset.scrap.noje2@example.com")
        frappe.set_user(email)
        summary = assets.get_summary(self.asset.name)
        self.assertFalse(summary["can"]["restore"],
                         "no Journal Entry cancel: the restore button must be hidden")
        with self.assertRaises(frappe.PermissionError):
            assets.restore(self.asset.name)

class TestLocationSpecificChecks(AssetApiTestCase):
    """The endpoints check the concrete Location the user types, not just any Location."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.email = "asset.loc.check@example.com"
        fixtures.ensure_user(self.email, "Location Check", ("Accounts User", "Stock Manager"))
        frappe.clear_cache(user=self.email)

    def tearDown(self):
        frappe.set_user("Administrator")

    def grant_location(self, location):
        # Test classes roll back once per class, so keep this idempotent across test methods
        frappe.set_user("Administrator")
        if not frappe.db.exists("User Permission", {"user": self.email, "allow": "Location", "for_value": location}):
            frappe.get_doc({"doctype": "User Permission", "user": self.email, "allow": "Location",
                            "for_value": location, "apply_to_all_doctypes": 1}).insert()
        frappe.clear_cache(user=self.email)

    def test_move_into_forbidden_location_is_refused(self):
        frappe.set_user("Administrator")
        asset = make_asset("Loc move asset")
        frappe.db.set_value("Asset", asset.name, "location", "انبار تهران")
        self.grant_location("انبار تهران")
        frappe.set_user(self.email)
        with self.assertRaises(frappe.PermissionError):
            movements.create([asset.name], "Transfer", target_location="دفتر مرکزی")
        self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "انبار تهران",
                         "refused move must not change the asset")

    def test_create_into_forbidden_location_is_refused(self):
        self.grant_location("انبار تهران")
        frappe.set_user(self.email)
        with self.assertRaises(frappe.PermissionError):
            assets.create(asset_name="Loc new", item_code=fixtures.ITEM, company=COMPANY,
                          location="دفتر مرکزی", purchase_date=add_days(nowdate(), -5),
                          available_for_use_date=nowdate(), net_purchase_amount=2500000)

    def test_create_into_allowed_location_succeeds(self):
        self.grant_location("انبار تهران")
        frappe.set_user(self.email)
        out = assets.create(asset_name="Loc new ok", item_code=fixtures.ITEM, company=COMPANY,
                            location="انبار تهران", purchase_date=add_days(nowdate(), -5),
                            available_for_use_date=nowdate(), net_purchase_amount=2500000)
        self.assertEqual(out["status"], "Submitted")


class TestFeatureFlagsUnderLocationScope(AssetApiTestCase):
    """The UI flags are site-wide; a Location User Permission can still restrict spawning data.
    These tests pin the split so the UI and the README stay honest about it."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.email = "asset.flag.scoped@example.com"
        fixtures.ensure_user(self.email, "Scope Flag", ("Accounts User", "Stock Manager"))
        frappe.clear_cache(user=self.email)

    def tearDown(self):
        frappe.set_user("Administrator")

    def grant(self, location):
        frappe.set_user("Administrator")
        if not frappe.db.exists("User Permission", {"user": self.email, "allow": "Location", "for_value": location}):
            frappe.get_doc({"doctype": "User Permission", "user": self.email, "allow": "Location",
                            "for_value": location, "apply_to_all_doctypes": 1}).insert()
        frappe.clear_cache(user=self.email)

    def test_flags_match_every_permission_the_endpoint_checks(self):
        # Stock User has no Asset create or write, so the create and movement buttons must be hidden
        email = "asset.flag.stockonly@example.com"
        fixtures.ensure_user(email, "Stock Only", ("Stock User",))
        frappe.clear_cache(user=email)
        frappe.set_user(email)
        feats = session.me()["features"]
        self.assertFalse(feats["asset_create"], "no Asset create: the create button must be hidden")
        self.assertFalse(feats["asset_movement"], "no Asset write: the movement button must be hidden")

    def test_flags_stay_true_but_specific_location_is_checked(self):
        feats_before = self.features_email = None
        frappe.set_user(self.email)
        self.assertTrue(session.me()["features"]["asset_create"])
        self.assertTrue(session.me()["features"]["asset_movement"])
        self.grant("دفتر مرکزی")
        frappe.set_user(self.email)
        self.assertTrue(session.me()["features"]["asset_create"],
                        "site-wide flag stays true; only the concrete location is refused")
        self.assertFalse(frappe.has_permission("Location", "read", "انبار تهران"))
        self.assertTrue(frappe.has_permission("Location", "read", "دفتر مرکزی"))
