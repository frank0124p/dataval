#!/usr/bin/env python3
"""DataHub 中介資料整合（datahub.py／datahub_client.py）的守門測試。

守的保證：
  D1 API 未接：七項全部 skipped、永不擋合規；每個面向只出一筆（不逐表重複）
  D2 判定：七項面向各自的合格／不合格判定（純函式、可預測）
  D3 卡控強度：off 不出、warning 不擋、error 才擋；設定檔覆寫得到
  D4 snapshot：契約檢查、壞檔與缺檔都回空殼（治理不因平台掛掉停擺）
  D5 client：Null／Fixture 的行為與 URN 組法；fetch 產出符合 snapshot 契約
  D6 報告：md／html／json 都帶得到，顧問區 prompt 也拿得到素材
  D7 查詢位置：input/<名>/datahub.yaml 可自行交代去平台哪裡拿；
     壞檔不擋（退回推導）；報告交代得出用的是宣告還是推導的位置
  D8 連結：填了 ui_url 報告就連得到平台，且各面向落在該看的分頁
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import datahub, datahub_client                       # noqa: E402
from dataval.model import ZONE_GATING                             # noqa: E402
from dataval.parser import parse_ddl                              # noqa: E402
from dataval.report import to_html, to_json, to_markdown          # noqa: E402

DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT '訂單', "
       "amount Decimal(18,2) COMMENT '金額') ENGINE = MergeTree() "
       "ORDER BY (order_id);")

GOOD = {
    "urn": "urn:li:dataset:x", "exists": True,
    "owners": [{"urn": "urn:li:corpuser:alice", "type": "BUSINESS_OWNER",
                "name": "Alice"}],
    "tags": ["PII"],
    "description": "訂單主檔：一列一筆訂單，承載成交事實。",
    "columns": {"order_id": {"description": "訂單編號"},
                "amount": {"description": "含稅金額"}},
    "lineage": {"upstreams": ["urn:li:dataset:ods_orders"], "downstreams": []},
    "access_grants": [{"ap": "報表AP", "level": "read", "granted": True}],
    "quality_checks": [{"name": "row_count", "last_run": "2026-09-07T00:00:00Z",
                        "status": "PASS"}],
}
BAD = {"urn": "urn:li:dataset:x", "exists": True, "owners": [], "tags": [],
       "description": "", "columns": {"order_id": {"description": ""}},
       "lineage": {"upstreams": [], "downstreams": []},
       "access_grants": [], "quality_checks": []}


def snap(entry, table="orders", unavailable=None, source="fixture"):
    return {"schema_version": 1, "source": source, "fetched_at": "2026-09-08T00:00:00Z",
            "server": "", "datasets": {table: entry},
            "unavailable": list(unavailable or [])}


def schema():
    return parse_ddl(DDL)


class D1Unavailable(unittest.TestCase):
    """API 未接：全部 skipped、不擋、每面向只出一筆。"""

    def test_no_snapshot_is_all_skipped(self):
        findings, meta = datahub.run(schema(),
                                     snapshot=datahub.empty_snapshot("測試"))
        self.assertEqual(len(findings), len(datahub.ASPECT_KEYS))
        self.assertTrue(all(f.status == "skipped" for f in findings))
        self.assertTrue(all(f.zone == ZONE_GATING for f in findings))
        self.assertTrue(all(f.severity == "info" for f in findings))
        self.assertEqual({f.check_id for f in findings}, set(datahub.CHECK_IDS))

    def test_skipped_is_one_per_aspect_not_per_table(self):
        multi = parse_ddl(DDL + " CREATE TABLE items (item_id UInt64 "
                          "COMMENT 'x') ENGINE = MergeTree() ORDER BY (item_id);")
        findings, _ = datahub.run(multi, snapshot=datahub.empty_snapshot("測試"))
        self.assertEqual(len(findings), 7)          # 不是 7×2
        self.assertTrue(all(f.target == "(schema)" for f in findings))

    def test_table_missing_from_platform_is_skipped_not_violation(self):
        findings, _ = datahub.run(schema(), snapshot=snap(GOOD, table="other"))
        self.assertTrue(all(f.status == "skipped" for f in findings))

    def test_disabled_produces_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "_engine"))
            with open(os.path.join(tmp, "_engine", "datahub.yaml"), "w",
                      encoding="utf-8") as handle:
                handle.write("enabled: false\n")
            findings, meta = datahub.run(schema(), config_dir=tmp)
        self.assertEqual(findings, [])
        self.assertEqual(meta, {})


class D2Evaluate(unittest.TestCase):
    """七項面向的判定。"""

    def _state(self, entry, aspect, settings=None):
        rows = datahub.evaluate(schema(), snap(entry),
                                settings or datahub.load_settings("/nonexistent"))
        return next(r for r in rows if r["aspect"] == aspect)["state"]

    def test_all_seven_pass_on_a_fully_governed_table(self):
        for aspect in datahub.ASPECT_KEYS:
            self.assertEqual(self._state(GOOD, aspect), "pass", aspect)

    def test_all_seven_flag_an_ungoverned_table(self):
        for aspect in datahub.ASPECT_KEYS:
            self.assertEqual(self._state(BAD, aspect), "violation", aspect)

    def test_owner_requires_a_business_owner_not_just_any_owner(self):
        entry = dict(GOOD, owners=[{"urn": "u:bob", "type": "TECHNICAL_OWNER",
                                    "name": "Bob"}])
        self.assertEqual(self._state(entry, "owner"), "violation")

    def test_required_tags_must_all_be_present(self):
        settings = dict(datahub.load_settings("/nonexistent"),
                        required_tags=["PII", "layer"])
        rows = datahub.evaluate(schema(), snap(GOOD), settings)
        row = next(r for r in rows if r["aspect"] == "tag")
        self.assertEqual(row["state"], "violation")
        self.assertIn("layer", row["actual"])

    def test_column_desc_coverage_threshold(self):
        entry = dict(GOOD, columns={"a": {"description": "x"},
                                    "b": {"description": ""}})
        self.assertEqual(self._state(entry, "column_desc"), "violation")
        loose = dict(datahub.load_settings("/nonexistent"),
                     column_desc_min_coverage=0.5)
        rows = datahub.evaluate(schema(), snap(entry), loose)
        self.assertEqual(next(r for r in rows
                              if r["aspect"] == "column_desc")["state"], "pass")

    def test_lineage_needs_upstreams_downstream_alone_is_not_enough(self):
        entry = dict(GOOD, lineage={"upstreams": [], "downstreams": ["x"]})
        self.assertEqual(self._state(entry, "lineage"), "violation")

    def test_required_grant_ap_must_be_covered(self):
        settings = dict(datahub.load_settings("/nonexistent"),
                        required_grant_aps=["風控AP"])
        rows = datahub.evaluate(schema(), snap(GOOD), settings)
        row = next(r for r in rows if r["aspect"] == "access_grant")
        self.assertEqual(row["state"], "violation")
        self.assertIn("風控AP", row["actual"])

    def test_quality_check_failing_or_never_run_is_a_violation(self):
        failed = dict(GOOD, quality_checks=[{"name": "q", "last_run": "t",
                                             "status": "FAIL"}])
        self.assertEqual(self._state(failed, "quality_check"), "violation")
        never = dict(GOOD, quality_checks=[{"name": "q", "status": "PASS"}])
        self.assertEqual(self._state(never, "quality_check"), "violation")


class D3Enforcement(unittest.TestCase):
    """off／warning／error 三段卡控。"""

    def _run(self, level):
        settings = datahub.load_settings("/nonexistent")
        settings["enforcement"] = {k: level for k in datahub.ASPECT_KEYS}
        rows = datahub.evaluate(schema(), snap(BAD), settings)
        return rows

    def test_warning_is_the_default_and_never_blocks(self):
        findings, _ = datahub.run(schema(), snapshot=snap(BAD))
        self.assertTrue(all(f.status == "warning" for f in findings))
        self.assertFalse(any(f.status == "fail" and f.severity == "error"
                             for f in findings))

    def test_off_produces_no_finding(self):
        self.assertTrue(all(r["state"] == "off" for r in self._run("off")))

    def test_error_level_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "_engine"))
            with open(os.path.join(tmp, "_engine", "datahub.yaml"), "w",
                      encoding="utf-8") as handle:
                handle.write("enforcement:\n  owner: error\n")
            findings, _ = datahub.run(schema(), config_dir=tmp,
                                      snapshot=snap(BAD))
        owner = [f for f in findings if f.check_id == "DATAHUB.OWNER"]
        self.assertEqual([f.status for f in owner], ["fail"])
        self.assertEqual(owner[0].severity, "error")
        others = [f for f in findings if f.check_id != "DATAHUB.OWNER"]
        self.assertTrue(all(f.status == "warning" for f in others))

    def test_settings_file_only_overrides_what_it_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "_engine"))
            with open(os.path.join(tmp, "_engine", "datahub.yaml"), "w",
                      encoding="utf-8") as handle:
                handle.write("platform: bigquery\nenforcement:\n  tag: off\n")
            settings = datahub.load_settings(tmp)
        self.assertEqual(settings["platform"], "bigquery")
        self.assertEqual(settings["enforcement"]["tag"], "off")
        self.assertEqual(settings["enforcement"]["owner"], "warning")
        self.assertEqual(settings["env"], "PROD")       # 未指名的保留預設

    def test_yaml_reads_bare_off_as_a_boolean_and_we_still_honour_it(self):
        # YAML 1.1：`tag: off` → False。設定檔裡這是最自然的寫法，不能靜默失效。
        self.assertEqual(datahub._level(False), "off")
        self.assertEqual(datahub._level("OFF"), "off")
        self.assertEqual(datahub._level("nonsense"), "")


class D4Snapshot(unittest.TestCase):
    """snapshot 契約與容錯。"""

    def test_missing_and_broken_snapshot_both_degrade_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(datahub.load_snapshot(tmp, "order")["source"],
                             "none")
            path = datahub.snapshot_path(tmp, "order", create=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{ not json")
            data = datahub.load_snapshot(tmp, "order")
            self.assertEqual(data["source"], "none")
            self.assertEqual(sorted(data["unavailable"]),
                             sorted(datahub.ASPECT_KEYS))

    def test_snapshot_lives_in_govern_doc_not_input(self):
        # 它是機器產物，不是使用者權威輸入——不該混進 input/
        path = datahub.snapshot_path("/x", "order")
        self.assertTrue(path.endswith("/govern_doc/order/order.datahub.json"),
                        path)
        self.assertNotIn("/input/", path)

    def test_validate_snapshot_catches_contract_breaks(self):
        self.assertEqual(datahub.validate_snapshot(snap(GOOD)), [])
        self.assertTrue(datahub.validate_snapshot({"datasets": []}))
        self.assertTrue(datahub.validate_snapshot(
            {"datasets": {}, "unavailable": ["nonsense"]}))
        self.assertTrue(datahub.validate_snapshot(
            {"datasets": {"t": {"owners": "not-a-list"}}}))


class D5Client(unittest.TestCase):
    """client 與抓取。"""

    def test_urn_follows_datahub_v0_13_3_shape(self):
        settings = dict(datahub.load_settings("/nonexistent"), container="dwd")
        self.assertEqual(
            datahub.dataset_urn("orders", settings),
            "urn:li:dataset:(urn:li:dataPlatform:clickhouse,dwd.orders,PROD)")

    def test_null_client_yields_a_fully_unavailable_snapshot(self):
        data = datahub_client.fetch(["orders"], datahub.load_settings("/x"),
                                    datahub_client.NullClient())
        self.assertEqual(data["source"], "none")
        self.assertEqual(sorted(data["unavailable"]),
                         sorted(datahub.ASPECT_KEYS))
        self.assertEqual(datahub.validate_snapshot(data), [])

    def test_fixture_client_round_trips_into_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"datasets": {"orders": GOOD}}, handle)
            client = datahub_client.FixtureClient(path)
            data = datahub_client.fetch(["orders"],
                                        datahub.load_settings("/x"), client)
        self.assertEqual(datahub.validate_snapshot(data), [])
        self.assertEqual(data["unavailable"], [])
        findings, _ = datahub.run(schema(), snapshot=data)
        self.assertTrue(all(f.status == "pass" for f in findings))

    def test_fixture_can_declare_partial_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"available": ["owner"],
                           "datasets": {"orders": GOOD}}, handle)
            data = datahub_client.fetch(["orders"],
                                        datahub.load_settings("/x"),
                                        datahub_client.FixtureClient(path))
        self.assertEqual(data["unavailable"],
                         [a for a in datahub.ASPECT_KEYS if a != "owner"])
        findings, _ = datahub.run(schema(), snapshot=data)
        statuses = {f.check_id: f.status for f in findings}
        self.assertEqual(statuses["DATAHUB.OWNER"], "pass")
        self.assertEqual(statuses["DATAHUB.TAG"], "skipped")

    def test_every_aspect_has_an_endpoint_and_a_parser(self):
        for aspect in datahub.ASPECT_KEYS:
            self.assertIn(aspect, datahub_client._ENDPOINTS, aspect)
            self.assertIn(aspect, datahub_client._PARSERS, aspect)
            self.assertIn(aspect, datahub_client._SNAPSHOT_FIELD, aspect)

    def test_http_client_only_offers_aspects_whose_base_url_is_set(self):
        settings = dict(datahub.load_settings("/x"), server="http://gms")
        self.assertEqual(datahub_client.HttpClient(settings).available(),
                         ["owner", "tag", "table_desc", "column_desc",
                          "lineage"])


class D6Report(unittest.TestCase):
    """報告與顧問區都看得到。"""

    def _meta(self, entry=GOOD):
        _, meta = datahub.run(schema(), snapshot=snap(entry))
        return {"dialect": "clickhouse", "tables": 1, "datahub": meta}

    def test_markdown_html_json_all_carry_the_section(self):
        meta = self._meta()
        findings, _ = datahub.run(schema(), snapshot=snap(GOOD))
        self.assertIn("## DataHub 中介資料", to_markdown(findings, meta))
        self.assertIn("DataHub 中介資料", to_html(findings, meta))
        payload = json.loads(to_json(findings, meta))
        self.assertEqual(len(payload["datahub"]["aspects"]), 7)

    def test_report_names_the_provider_so_you_know_which_api_to_chase(self):
        providers = {a["aspect"]: a["provider"]
                     for a in self._meta()["datahub"]["aspects"]}
        self.assertEqual(providers["access_grant"], "自建 API")
        self.assertEqual(providers["quality_check"], "自建 API")
        self.assertTrue(providers["owner"].startswith("DataHub"))

    def test_console_and_advisory_material_distinguish_connected(self):
        connected = self._meta()["datahub"]
        self.assertIn("通過", datahub.console_lines(connected)[0])
        self.assertIn("業務負責人", datahub.advisory_material(connected))
        _, offline = datahub.run(schema(),
                                 snapshot=datahub.empty_snapshot("測試"))
        self.assertIn("未接 API", datahub.console_lines(offline)[0])
        self.assertIn("尚未接上", datahub.advisory_material(offline))


class D7Targets(unittest.TestCase):
    """去平台哪裡拿——input 可自行交代。"""

    def _write(self, tmp, body):
        ddl_path = os.path.join(tmp, "order.sql")
        open(ddl_path, "w").close()
        with open(os.path.join(tmp, datahub.TARGETS_NAME), "w",
                  encoding="utf-8") as handle:
            handle.write(body)
        return ddl_path

    def test_no_file_means_derive_from_table_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets, problems = datahub.load_targets(
                os.path.join(tmp, "order.sql"))
        self.assertEqual((targets, problems), ({}, []))
        target = datahub.resolve_target("orders",
                                        datahub.load_settings("/nonexistent"))
        self.assertFalse(target["declared"])
        self.assertIn("clickhouse,orders,PROD", target["urn"])

    def test_subject_defaults_and_per_table_overrides_compose(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "container: dwd\ntables:\n"
                                    "  order_items:\n    name: detail\n"
                                    "    container: dwm\n")
            targets, problems = datahub.load_targets(path)
        self.assertEqual(problems, [])
        settings = datahub.load_settings("/nonexistent")
        # subject 預設套到沒宣告的表
        self.assertIn("clickhouse,dwd.orders,PROD",
                      datahub.resolve_target("orders", settings, targets)["urn"])
        # 逐表覆寫贏過 subject 預設
        item = datahub.resolve_target("order_items", settings, targets)
        self.assertIn("clickhouse,dwm.detail,PROD", item["urn"])
        self.assertTrue(item["declared"])

    def test_explicit_urn_wins_over_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "container: dwd\ntables:\n  orders:\n"
                                    '    urn: "urn:li:dataset:hand-written"\n')
            targets, _ = datahub.load_targets(path)
        self.assertEqual(
            datahub.resolve_target("orders", datahub.load_settings("/x"),
                                   targets)["urn"],
            "urn:li:dataset:hand-written")

    def test_self_hosted_api_keys_fall_back_to_the_urn(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "tables:\n  orders:\n"
                                    '    grant_key: "PAY_TABLE"\n')
            targets, _ = datahub.load_targets(path)
        target = datahub.resolve_target("orders", datahub.load_settings("/x"),
                                        targets)
        self.assertEqual(target["grant_key"], "PAY_TABLE")
        self.assertEqual(target["quality_key"], target["urn"])

    def test_broken_or_unknown_keys_warn_but_never_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "tables:\n  orders:\n    nonsense: 1\n")
            targets, problems = datahub.load_targets(path)
        self.assertTrue(problems)
        findings, _ = datahub.run(schema(), snapshot=snap(GOOD),
                                  targets=targets, target_problems=problems)
        broken = [f for f in findings if f.check_id == "SYSTEM.CONFIG_SPEC"]
        self.assertEqual([f.status for f in broken], ["warning"])
        self.assertFalse(any(f.status == "fail" for f in findings))

    def test_unparseable_file_degrades_to_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "tables: [this is not a mapping\n")
            targets, problems = datahub.load_targets(path)
        self.assertEqual(targets, {})
        self.assertTrue(problems)

    def test_report_says_whether_the_location_was_declared_or_derived(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "tables:\n  orders:\n    container: dwd\n")
            targets, _ = datahub.load_targets(path)
        _, meta = datahub.run(schema(), snapshot=snap(GOOD), targets=targets)
        self.assertEqual(meta["declared_targets"], 1)
        row = meta["targets"][0]
        self.assertEqual(row["table"], "orders")
        self.assertIn("宣告", row["origin"])
        self.assertIn("### 查詢位置",
                      "\n".join(to_markdown([], {"datahub": meta}).splitlines()))


class D8Links(unittest.TestCase):
    """報告連得到 DataHub。"""

    def _meta(self, ui="https://datahub.example.com"):
        settings = dict(datahub.load_settings("/nonexistent"), ui_url=ui)
        rows = datahub.evaluate(schema(), snap(GOOD), settings)
        targets = datahub.resolve_targets(["orders"], settings, None)
        return datahub.report_meta(snap(GOOD), settings, rows, targets)

    def test_ui_url_turns_tables_into_links_on_the_right_tab(self):
        meta = self._meta()
        target = meta["targets"][0]
        self.assertTrue(target["link"].startswith(
            "https://datahub.example.com/dataset/urn:li:dataset:"))
        self.assertTrue(datahub.aspect_link(target, "lineage")
                        .endswith("/Lineage"))
        self.assertTrue(datahub.aspect_link(target, "column_desc")
                        .endswith("/Schema"))
        self.assertTrue(datahub.aspect_link(target, "quality_check")
                        .endswith("/Validation"))
        self.assertFalse(datahub.aspect_link(target, "owner").endswith("/"))

    def test_no_ui_url_means_no_links_anywhere(self):
        meta = self._meta(ui="")
        self.assertEqual(meta["targets"][0]["link"], "")
        self.assertEqual(datahub.aspect_link(meta["targets"][0], "lineage"), "")

    def test_markdown_wraps_urls_so_parens_in_the_urn_do_not_break_them(self):
        # URN 含 ( ) ,——不用 <…> 包住的話網址會在第一個右括號被截斷
        text = to_markdown([], {"datahub": self._meta()})
        self.assertIn("](<https://datahub.example.com/dataset/", text)
        self.assertNotIn("](https://datahub.example.com/dataset/", text)

    def test_html_renders_real_anchors(self):
        html = to_html([], {"datahub": self._meta()})
        self.assertIn('href="https://datahub.example.com/dataset/', html)
        self.assertIn('target="_blank"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
