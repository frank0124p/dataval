"""正式區全域關聯圖與晉升流程的守門測試。

守的保證：
  G1 全域循環（含候選邊）→ 會擋
  G2 同一對端點的基數矛盾 → 會擋
  G3 候選表在正式區有依賴者 → 影響分析（資訊，不擋）
  G4 全區健檢：斷鏈 fail、legacy 平鋪 warn、規則版本碼 drift warn
  G5 晉升閘門：不合規的 subject 不能晉升；晉升記錄帶雙碼
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import yaml  # noqa: E402

from dataval import prodgraph  # noqa: E402
from dataval.parser import parse_ddl  # noqa: E402
from dataval.precheck import _parse_endpoint  # noqa: E402


def write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_subject(prod: str, domain: str, name: str, ddl: str,
                 relations_yaml: str = "relations: []\n",
                 promotion: dict | None = None):
    base = os.path.join(prod, domain, name)
    write(os.path.join(base, f"{name}.sql"), ddl)
    write(os.path.join(base, f"{name}.relations.yaml"), relations_yaml)
    write(os.path.join(base, f"{name}.context.md"),
          f"---\nsubject: {name}\n---\n## 粒度\n一行=一筆。\n")
    if promotion is not None:
        with open(os.path.join(base, "_promotion.yaml"), "w",
                  encoding="utf-8") as f:
            yaml.safe_dump(promotion, f, allow_unicode=True)
    return base


def rel(from_: str, to: str, card: str = "N:1") -> dict:
    return {"from": from_, "to": to, "cardinality": card,
            "_from": _parse_endpoint(from_), "_to": _parse_endpoint(to)}


DDL_A = ("CREATE TABLE a (a_id UInt64 COMMENT 'x', b_id UInt64 COMMENT 'y') "
         "ENGINE=MergeTree() ORDER BY (a_id);")
DDL_B = ("CREATE TABLE b (b_id UInt64 COMMENT 'x', a_id UInt64 COMMENT 'y') "
         "ENGINE=MergeTree() ORDER BY (b_id);")


class ProdgraphCase(unittest.TestCase):
    def setUp(self):
        self.prod = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.prod)


class T_G1_GlobalCycleBlocks(ProdgraphCase):
    def test_candidate_edge_closes_cycle(self):
        # 正式區：a 依賴 b（b 是上游）。候選宣告 b 依賴 a → 循環。
        make_subject(self.prod, "X", "subj_a", DDL_A,
                     "relations:\n  - from: a.b_id\n    to: b.b_id\n"
                     "    cardinality: \"N:1\"\n")
        schema = parse_ddl(DDL_B)
        findings = prodgraph.run(schema, [rel("b.a_id", "a.a_id")], self.prod)
        cycle = [f for f in findings if f.check_id == "PRODGRAPH.CYCLE"]
        self.assertEqual("fail", cycle[0].status)
        self.assertEqual("gating", cycle[0].zone)


class T_G2_CardinalityConflictBlocks(ProdgraphCase):
    def test_same_pair_different_cardinality(self):
        make_subject(self.prod, "X", "subj_a", DDL_A,
                     "relations:\n  - from: a.b_id\n    to: b.b_id\n"
                     "    cardinality: \"N:1\"\n")
        schema = parse_ddl(DDL_A)
        findings = prodgraph.run(
            schema, [rel("a.b_id", "b.b_id", "N:M")], self.prod)
        conflict = [f for f in findings
                    if f.check_id == "PRODGRAPH.CARDINALITY_CONFLICT"]
        self.assertEqual("fail", conflict[0].status)

    def test_same_cardinality_passes(self):
        make_subject(self.prod, "X", "subj_a", DDL_A,
                     "relations:\n  - from: a.b_id\n    to: b.b_id\n"
                     "    cardinality: \"N:1\"\n")
        schema = parse_ddl(DDL_A)
        findings = prodgraph.run(
            schema, [rel("a.b_id", "b.b_id", "N:1")], self.prod)
        conflict = [f for f in findings
                    if f.check_id == "PRODGRAPH.CARDINALITY_CONFLICT"]
        self.assertEqual("pass", conflict[0].status)


class T_G3_ImpactAnalysisInfo(ProdgraphCase):
    def test_dependents_listed_as_info(self):
        # 正式區 subj_a 依賴表 b；候選 DDL 定義了 b → 影響分析。
        make_subject(self.prod, "X", "subj_a", DDL_A,
                     "relations:\n  - from: a.b_id\n    to: b.b_id\n"
                     "    cardinality: \"N:1\"\n")
        schema = parse_ddl(DDL_B)
        findings = prodgraph.run(schema, [], self.prod)
        impact = [f for f in findings if f.check_id == "PRODGRAPH.IMPACT"]
        self.assertEqual(1, len(impact))
        self.assertEqual("info", impact[0].status)
        self.assertEqual("advisory", impact[0].zone)
        self.assertIn("X/subj_a", impact[0].message)


class T_G4_Audit(ProdgraphCase):
    def test_broken_link_fails_and_drift_warns(self):
        make_subject(
            self.prod, "X", "subj_a", DDL_A,
            "relations:\n  - from: a.b_id\n    to: ghost.b_id\n"
            "    cardinality: \"N:1\"\n",
            promotion={"rule_version_code": "old_code"})
        result = prodgraph.audit(self.prod, rule_code="new_code")
        levels = {(lvl, msg.split("：")[0]) for lvl, _, msg in result["rows"]}
        self.assertFalse(result["ok"])
        self.assertIn(("fail", "斷鏈"), levels)
        self.assertIn(("warn", "規則版本碼 drift"), levels)

    def test_legacy_flat_ddl_warns(self):
        write(os.path.join(self.prod, "X", "old_table.sql"), DDL_A)
        result = prodgraph.audit(self.prod)
        self.assertTrue(any(lvl == "warn" and "舊式平鋪" in msg
                            for lvl, _, msg in result["rows"]))
        self.assertTrue(result["ok"])  # legacy 只提醒不 fail


class T_G5_PromotionGate(unittest.TestCase):
    def test_noncompliant_subject_cannot_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "input")
            rep = os.path.join(tmp, "reports")
            prod = os.path.join(tmp, "production")
            write(os.path.join(inp, "bad.sql"), DDL_A)
            write(os.path.join(inp, "bad.relations.yaml"), "relations: []\n")
            write(os.path.join(inp, "bad.context.md"),
                  "---\nsubject: bad\ndomains: [X]\n---\n## 粒度\n一行=一筆。\n")
            write(os.path.join(rep, "bad.report.json"), json.dumps(
                {"summary": {"compliant": False},
                 "blocking_summary": {"blocked": [{"rule": "SKILL.x"}]},
                 "findings": []}))
            env = dict(os.environ, DATAVAL_INPUT_DIR=inp,
                       DATAVAL_REPORT_DIR=rep, DATAVAL_PRODUCTION_DIR=prod,
                       PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run(
                [sys.executable, os.path.join(ROOT, "promote.py"), "bad"],
                cwd=ROOT, env=env, text=True, capture_output=True, check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("不合規", result.stderr)
            self.assertFalse(os.path.isdir(os.path.join(prod, "X", "bad")))

    def test_gate_result_code_is_order_insensitive(self):
        import promote
        f1 = {"check_id": "A", "status": "pass", "target": "t", "zone": "gating"}
        f2 = {"check_id": "B", "status": "fail", "target": "u", "zone": "gating"}
        adv = {"check_id": "C", "status": "info", "target": "v",
               "zone": "advisory"}
        a = promote.gate_result_code({"findings": [f1, f2, adv]})
        b = promote.gate_result_code({"findings": [f2, f1]})  # 順序無關、顧問區不計
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
