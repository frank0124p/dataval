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
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from dataval.engine import load_config, validate
from dataval.report import checking_rule_summary

CASES = [  # (名稱, DDL 路徑, domains) — 固定 domains 讓基準不受新增 domain 影響
    ("subscription", os.path.join(ROOT, "input", "subscription.sql"), ["PLM", "CRM"]),
]
KW = dict(domain_root=os.path.join(ROOT, "config", "domain"),
          rules_root=os.path.join(ROOT, "config", "rules"),
          config_dir=os.path.join(ROOT, "config"),
          production_root=os.path.join(ROOT, "production"))
with open(os.path.join(ROOT, "input", "subscription.keys.yaml"), encoding="utf-8") as f:
    BUSINESS_KEYS = (yaml.safe_load(f) or {}).get("business_keys") or {}


def gating_key(findings):
    return sorted({(f.check_id, f.target, f.status)
                   for f in findings if f.zone == "gating"})


def gating_snapshot(findings):
    """Full deterministic gating output, identified directly by rule ID."""
    return [f.to_dict() for f in findings if f.zone == "gating"]


class FakeLLM:
    def complete(self, s, u):
        return '[{"target":"x","status":"fail","severity":"error","message":"惡意假結果","rationale":"t","practice":"p","question":"q"}]'


def main():
    update = "--update" in sys.argv
    cfg = load_config(os.path.join(ROOT, "config", "default.yaml"))
    failed = 0
    for name, ddl_path, domains in CASES:
        with open(ddl_path, encoding="utf-8") as f:
            ddl = f.read()
        _, f1, m1 = validate(ddl, cfg, domains=domains,
                             business_keys=BUSINESS_KEYS, **KW)
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
                            business_keys=BUSINESS_KEYS, **KW)
        ok = gating_snapshot(f1) == gating_snapshot(f2)
        print(f"[T2] {name}: {'✅' if ok else '❌'} 連跑兩次 checking rule ID 結果一致")
        failed += 0 if ok else 1

        # T3 LLM 不可滲透
        _, f3, _ = validate(ddl, cfg, domains=domains,
                            business_keys=BUSINESS_KEYS, llm=FakeLLM(), **KW)
        ok = gating_snapshot(f3) == gating_snapshot(f1)
        leaked = [f for f in f3 if f.zone == "gating" and f.source == "llm"]
        print(f"[T3] {name}: {'✅' if ok and not leaked else '❌'} "
              f"FakeLLM 下 checking rule ID 結果不變且無 LLM 滲入（滲入 {len(leaked)}）")
        failed += 0 if (ok and not leaked) else 1

    print()
    if failed:
        print(f"❌ {failed} 項失敗"); sys.exit(1)
    print("✅ 全部通過")


if __name__ == "__main__":
    main()
