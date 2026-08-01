#!/usr/bin/env python3
"""黃金測試 — 卡控一致性的守門員。

    python tests/golden_test.py            # 跑全部測試
    python tests/golden_test.py --update   # 重建黃金基準（規則刻意演化後用）

三類測試：
  T1 黃金比對：基準 DDL 的閘門區輸出（check_id, target, status 集合）
     必須與 tests/golden/*.json 完全一致 —— 防止改 A 規則誤傷 B。
  T2 確定性：同輸入連跑兩次，每條 checking rule ID 的閘門結果相同。
  T3 LLM 不可滲透：接上會亂回傳的 FakeLLM，checking rule ID 結果不得改變。
"""
from __future__ import annotations
import json
import os
import sys
import unittest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from dataval.engine import load_config, validate
from dataval.precheck import locate_pieces, parse_context
from dataval.report import checking_rule_summary

CASES = [  # (名稱, DDL 路徑, domains) — 固定 domains 讓基準不受新增 domain 影響
    ("subscription", os.path.join(ROOT, "input", "subscription", "subscription.sql"), ["PLM", "CRM"]),
    ("order", os.path.join(ROOT, "input", "order", "order.sql"), ["CRM"]),
]
KW = dict(domain_root=os.path.join(ROOT, "config"),
          rules_root=os.path.join(ROOT, "config", "Common", "knowhow_py"),
          config_dir=os.path.join(ROOT, "config"),
          production_root=os.path.join(ROOT, "production"))


def business_keys_for(ddl_path: str) -> dict:
    """優先取 subject 自己的 context.md front-matter；
    無宣告時退回 Common/cases 的 legacy fixture（subscription 用）。"""
    context_path = locate_pieces(ddl_path)["context"]
    if os.path.isfile(context_path):
        with open(context_path, encoding="utf-8") as f:
            meta, _ = parse_context(f.read())
        keys = meta.get("business_keys") or {}
        if keys:
            return {str(t): [str(c) for c in cols] for t, cols in keys.items()}
    name = os.path.splitext(os.path.basename(ddl_path))[0]
    fixture = os.path.join(ROOT, "config", "Common", "cases", f"{name}.yaml")
    if os.path.isfile(fixture):
        with open(fixture, encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("business_keys") or {}
    return {}


def gating_key(findings):
    return sorted({(f.check_id, f.target, f.status)
                   for f in findings if f.zone == "gating"})


def gating_snapshot(findings):
    """Full deterministic gating output, identified directly by rule ID."""
    return [f.to_dict() for f in findings if f.zone == "gating"]


class FakeLLM:
    def complete(self, s, u):
        return '[{"target":"x","status":"fail","severity":"error","message":"惡意假結果","rationale":"t","practice":"p","question":"q"}]'


def run_cases(update: bool = False) -> int:
    cfg = load_config(os.path.join(ROOT, "config", "_engine", "default.yaml"))
    failed = 0
    for name, ddl_path, domains in CASES:
        with open(ddl_path, encoding="utf-8") as f:
            ddl = f.read()
        business_keys = business_keys_for(ddl_path)
        _, f1, m1 = validate(ddl, cfg, domains=domains,
                             business_keys=business_keys, **KW)
        golden_path = os.path.join(HERE, "golden", name + ".json")

        # T1 黃金比對
        got = [list(x) for x in gating_key(f1)]
        got_rule_summary = checking_rule_summary(f1, m1.get("checking_rule_ids_loaded"))
        if update:
            with open(golden_path, "w", encoding="utf-8") as f:
                json.dump({"gating": got,
                           "checking_rule_summary": got_rule_summary},
                          f, ensure_ascii=False, indent=1)
            print(f"[T1] {name}: 黃金基準已更新（{len(got)} 條）")
        elif not os.path.isfile(golden_path):
            print(f"[T1] {name}: ❌ 缺黃金基準，先跑 --update"); failed += 1
        else:
            with open(golden_path, encoding="utf-8") as f:
                golden = json.load(f)
            want = golden["gating"]
            want_rule_summary = golden.get("checking_rule_summary")
            if got == want and got_rule_summary == want_rule_summary:
                print(f"[T1] {name}: ✅ 閘門輸出與 checking rule ID 摘要"
                      f"均與黃金基準一致（{len(got)} 條）")
            else:
                extra = [x for x in got if x not in want]
                missing = [x for x in want if x not in got]
                summary_changed = got_rule_summary != want_rule_summary
                print(f"[T1] {name}: ❌ 不一致 多出{len(extra)} 少了{len(missing)} "
                      f"rule ID 摘要變更={summary_changed}")
                for x in (extra + missing)[:5]:
                    print("      ", x)
                failed += 1

        # T2 確定性
        _, f2, _ = validate(ddl, cfg, domains=domains,
                            business_keys=business_keys, **KW)
        ok = gating_snapshot(f1) == gating_snapshot(f2)
        print(f"[T2] {name}: {'✅' if ok else '❌'} 連跑兩次 checking rule ID 結果一致")
        failed += 0 if ok else 1

        # T3 LLM 不可滲透
        _, f3, _ = validate(ddl, cfg, domains=domains,
                            business_keys=business_keys, llm=FakeLLM(), **KW)
        ok = gating_snapshot(f3) == gating_snapshot(f1)
        leaked = [f for f in f3 if f.zone == "gating" and f.source == "llm"]
        print(f"[T3] {name}: {'✅' if ok and not leaked else '❌'} "
              f"FakeLLM 下 checking rule ID 結果不變且無 LLM 滲入（滲入 {len(leaked)}）")
        failed += 0 if (ok and not leaked) else 1
    return failed


class GoldenTest(unittest.TestCase):
    """讓黃金測試進 unittest discovery——CLI 忘了跑也不會靜默漂移。"""

    def test_golden_cases(self):
        self.assertEqual(0, run_cases(update=False),
                         "黃金測試失敗——明細見 stdout；刻意演化規則後用 "
                         "python tests/golden_test.py --update 重建基準")


def main():
    failed = run_cases(update="--update" in sys.argv)
    print()
    if failed:
        print(f"❌ {failed} 項失敗"); sys.exit(1)
    print("✅ 全部通過")


if __name__ == "__main__":
    main()
