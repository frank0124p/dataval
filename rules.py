#!/usr/bin/env python3
"""gating/advisory 規則管理工具 — 讓規則維護保持「一條一檔、快速新增」。

    python rules.py list                     # 盤點目前載入的所有規則
    python rules.py new <domain> <gating|advisory> <rule_id>   # 從範本秒生新規則
    python rules.py lint                     # 檢查所有規則檔語法（不跑完整驗證）
    python rules.py compile                  # 手動 compile 規則成 build/compiled_rules.json
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SKILLS = os.path.join(HERE, "config", "skills")
SKILLS_PY = os.path.join(HERE, "config", "skills_py")
TEMPLATES = os.path.join(HERE, "config", "templates")

from dataval.skills import SkillRegistry
from dataval.skills.markdown_skill import load_markdown_skill


def cmd_list():
    reg = SkillRegistry()
    reg.load_domains(SKILLS, domains=None, py_dir=SKILLS_PY)
    print(f"{'規則 id':36} {'等級':9} {'類別':14} {'domain':8} 檔案")
    print("-" * 100)
    for s in sorted(reg.markdown, key=lambda x: (getattr(x, 'domain', ''), x.id)):
        kind = s.enforcement + ("" if s.check_lines else "(llm)" if s.check_llm else "")
        print(f"{s.id:36} {kind:9} {s.category:14} {getattr(s,'domain','?'):8} "
              f"{os.path.relpath(s.path, HERE)}")
    for m in reg.imperative:
        meta = m.SKILL_META
        print(f"{meta.get('id','?'):36} {'py':9} {meta.get('category','?'):14} "
              f"{meta.get('domain','common'):8} "
              f"config/skills_py/{os.path.basename(m.__dict__.get('__file__','') or m.__name__+'.py')}")
    print(f"\n共 {len(reg.markdown)} 條 .md 規則 ＋ {len(reg.imperative)} 條 py 規則")


def cmd_new(domain: str, zone: str, rule_id: str):
    if zone not in ("gating", "advisory"):
        sys.exit("zone 必須是 gating 或 advisory")
    tpl = os.path.join(TEMPLATES, f"skill_{zone}.template.md")
    dst_dir = os.path.join(SKILLS, domain, zone)
    dst = os.path.join(dst_dir, f"{rule_id}.md")
    if os.path.exists(dst):
        sys.exit(f"已存在：{dst}")
    os.makedirs(dst_dir, exist_ok=True)
    text = open(tpl, encoding="utf-8").read().replace(
        "<唯一代號_小寫英數底線>", rule_id)
    open(dst, "w", encoding="utf-8").write(text)
    print(f"已建立 {os.path.relpath(dst, HERE)}")
    print("下一步：填 category / enforcement 與卡控內容，然後 python rules.py lint")


def cmd_lint():
    problems = 0
    for dirpath, _, files in os.walk(SKILLS):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, HERE)
            try:
                sk = load_markdown_skill(path)
            except Exception as e:
                print(f"❌ {rel}: {e}")
                problems += 1
                continue
            for u in sk.unparsed:
                print(f"❌ {rel}: 卡控語句無法解析 → {u}")
                problems += 1
            if not sk.check_lines and not sk.check_llm:
                print(f"⚠️  {rel}: 沒有任何卡控區塊（```check / ```check-llm）")
    if problems:
        print(f"\n{problems} 個問題"); sys.exit(1)
    print("✅ 所有規則檔語法正確")


def cmd_compile():
    from dataval.compiler import ensure_compiled
    path, recompiled = ensure_compiled(SKILLS, SKILLS_PY,
                                       os.path.join(HERE, "build", "compiled_rules.json"))
    print(("已重新 compile → " if recompiled else "規則未變，沿用 → ") + os.path.relpath(path, HERE))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "compile":
        cmd_compile()
    elif len(sys.argv) >= 2 and sys.argv[1] == "list":
        cmd_list()
    elif len(sys.argv) == 5 and sys.argv[1] == "new":
        cmd_new(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) >= 2 and sys.argv[1] == "lint":
        cmd_lint()
    else:
        print(__doc__)
