#!/usr/bin/env python3
"""抓 DataHub／自建 API 的中介資料，寫成 snapshot 供 govern mode 使用。

    python datahub_fetch.py              # 所有 input/ 下的 subject
    python datahub_fetch.py order        # 指定 subject
    python datahub_fetch.py --check      # 只看會抓到什麼，不寫檔

這是整包裡**唯一會連網**的入口。run.py 不連網——它只讀這支寫出來的
`input/<名>/datahub.json`。分開的理由：報告要能位元組穩定重現、審計時要能
回頭看「當時平台上是什麼樣」，以及平台掛掉時治理流程照跑。

設定在 `config/_engine/datahub.yaml`；token 從 `$DATAHUB_TOKEN` 讀。
API 還沒接上時照樣可以跑：snapshot 會標成全部 unavailable，
govern report 的七項中介資料檢查顯示 skipped，不影響合規判定。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from dataval import datahub, datahub_client
from dataval.parser import parse_ddl

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, "input")
CONFIG_DIR = os.path.join(HERE, "config")


def _subjects(names: list[str]) -> list[tuple[str, str]]:
    """[(subject, ddl_path)]；沿用 input/<名>/<名>.sql 的輸入契約。"""
    out = []
    for name in sorted(names or os.listdir(INPUT_DIR)):
        path = os.path.join(INPUT_DIR, name, f"{name}.sql")
        if os.path.isfile(path):
            out.append((name, path))
    return out


def _tables(ddl_path: str) -> list[str]:
    with open(ddl_path, encoding="utf-8") as handle:
        return [t.name for t in parse_ddl(handle.read()).tables]


def main() -> int:
    parser = argparse.ArgumentParser(description="抓 DataHub 中介資料 snapshot")
    parser.add_argument("subjects", nargs="*", help="要抓的 subject（預設全部）")
    parser.add_argument("--check", action="store_true", help="只顯示，不寫檔")
    args = parser.parse_args()

    settings = datahub.load_settings(CONFIG_DIR)
    if not settings.get("enabled", True):
        print("DataHub 整合已在 config/_engine/datahub.yaml 關閉（enabled: false）。")
        return 0
    client = datahub_client.make_client(settings)
    available = client.available()
    print(f"client：{client.name} ｜ 可提供面向："
          + ("、".join(available) if available else "（無——API 尚未接上）"))
    if not available:
        print("  ↳ 這是正常狀態：接上 API 前 govern report 的七項中介資料檢查"
              "顯示 skipped，不影響合規判定。")
        print("  ↳ 想先把流程跑通：在 config/_engine/datahub.yaml 設 fixture，"
              "或 export DATAHUB_FIXTURE=<某份 JSON>。")

    targets = _subjects(args.subjects)
    if not targets:
        print("找不到任何 subject（input/<名>/<名>.sql）。", file=sys.stderr)
        return 1
    for name, ddl_path in targets:
        try:
            tables = _tables(ddl_path)
        except Exception as error:
            print(f"  ⏭ {name}：DDL 無法解析，略過（{error}）")
            continue
        snapshot = datahub_client.fetch(tables, settings, client)
        problems = datahub.validate_snapshot(snapshot)
        if problems:
            print(f"  ❌ {name}：snapshot 不符契約 → " + "；".join(problems),
                  file=sys.stderr)
            return 1
        found = sum(1 for e in snapshot["datasets"].values() if e.get("exists"))
        path = datahub.snapshot_path(ddl_path)
        if args.check:
            print(f"  🔍 {name}：{len(tables)} 表，平台上找到 {found} 張"
                  f"（不寫檔）→ 會寫到 {os.path.relpath(path, HERE)}")
            continue
        body = json.dumps(snapshot, ensure_ascii=False, indent=2,
                          sort_keys=True) + "\n"
        old = ""
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                old = handle.read()
        if body != old:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)
        print(f"  ✅ {name}：{len(tables)} 表，平台上找到 {found} 張 → "
              f"{os.path.relpath(path, HERE)}")
        for error in snapshot.get("errors") or []:
            print(f"     ⚠️ {error}")
    print("完成。接著跑 python run.py，報告的「DataHub 中介資料」區塊就會"
          "帶上這份 snapshot。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
