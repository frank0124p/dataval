"""Config 檔案格式正規化（pre-run auto-format）。

`config/` 底下每個資料夾都有各自的載入格式（見各資料夾的 README）。
放錯格式最難查的失敗是**靜默不載入**——檔案在那裡、看起來也對，引擎卻讀不到。
這個模組在 run.py 起跑前先依**資料夾路徑**把檔案補成引擎吃得下的形狀：

  <域>/erd/*.md          ER 模型要在 ```mermaid fence 內  → 沒 fence 就包起來
  <域>/erd/tables/*.md   參考表用途要有 `# <表名>` 標題    → 沒標題就補
  <域>/flows/*.md        flowchart 要在 fence 內＋要有標題 → 兩者都補
  <域>/naming/*.md       對照表要在可辨識段落標題底下      → 依表頭關鍵字補標題
  <域>/business/*.md     業務描述／狀態機／時序圖…萬用夾    → 圖沒 fence 就包、
                         （什麼圖都收，格式不對也照樣載入）  缺標題就補
  <域>/knowhow/{gating,advisory}/*.md
                         規則檔要有 front-matter（category／enforcement）
                         與正確的卡控 fence 標籤            → 依資料夾與檔名補齊
  各資料夾                 副檔名不對 → 引擎根本不掃         → 改成正確副檔名

**只補格式與結構，不動語意內容**：不改詞條、不改關係、不改用途描述的字，
只做「包 fence／補標題／改副檔名」這類讓檔案能被載入的包裝。判斷不出來的
（例如看不出是禁用詞還是別名的對照表）一律不猜，留給 `config_check.py` 報。

冪等：已經是正確格式的檔案不會被改寫（位元組穩定），跑幾次結果都一樣。
"""
from __future__ import annotations

import os
import re

#: 已經是正確副檔名就不動；key＝資料夾類型，value＝{錯副檔名: 正確副檔名}
_RENAME: dict[str, dict[str, str]] = {
    "erd": {".markdown": ".md", ".txt": ".md"},
    "tables": {".markdown": ".md", ".txt": ".md"},
    "flows": {".markdown": ".md", ".txt": ".md",
              ".yaml": ".flow.yaml", ".yml": ".flow.yaml"},
    "naming": {".markdown": ".md", ".txt": ".md"},
    "business": {".markdown": ".md", ".txt": ".md", ".mmd": ".md",
                 ".mermaid": ".md"},
    "knowhow": {".markdown": ".md", ".txt": ".md"},
    "ssot": {},
}

#: 各資料夾接受的副檔名（用來判斷「這個檔會不會被載入」）
_ACCEPTED: dict[str, tuple[str, ...]] = {
    "erd": (".md", ".mmd", ".mermaid"),
    "tables": (".md",),
    "flows": (".md", ".flow.yaml", ".flow.yml"),
    "naming": (".md", ".yaml"),
    "business": (".md",),
    "knowhow": (".md",),
    "ssot": (".yaml",),
}

_FENCE = "```mermaid"
#: 業務素材什麼圖都收——這串只用來認出「這段是 mermaid 圖」好幫它包 fence
_ANY_DIAGRAM = ("stateDiagram(?:-v2)?|sequenceDiagram|erDiagram|flowchart"
                "|graph|journey|gantt|classDiagram|mindmap|timeline"
                "|pie|quadrantChart|requirementDiagram|C4Context")
_TITLE_RE = re.compile(r"^#\s+\S", re.MULTILINE)
#: 詞彙字典的段落標題關鍵字（與 engine._glossary_sections 同一組）
_SECTION_RE = re.compile(r"^#{1,6}\s+.*(禁用|縮寫|banned|forbidden|別名|alias"
                         r"|同義|標準|standard|白名單)", re.MULTILINE | re.I)
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
#: 表頭關鍵字 → 要補的段落標題
_HEADER_HINTS = (
    (re.compile(r"禁用|縮寫|banned|forbidden", re.I), "## 禁用詞"),
    (re.compile(r"別名|alias|同義", re.I), "## 別名"),
    (re.compile(r"標準|standard|白名單", re.I), "## 標準詞"),
)


#: 規則檔 front-matter 的合法值（與 skills/markdown_skill.py 同一組）
VALID_CATEGORIES = ("structural", "naming", "best_practice", "ssot")

#: 檔名／id 的既有命名慣例 → category（推不出來就不補，留給 compile 報）
_CATEGORY_HINTS = (
    (re.compile(r"^(?:naming|name)_|naming"), "naming"),
    (re.compile(r"^(?:structural|struct)_|structural"), "structural"),
    (re.compile(r"^(?:bp|best_practice)_|best_practice"), "best_practice"),
    (re.compile(r"^ssot_|ssot"), "ssot"),
)

#: 卡控 fence 的標籤：常見寫法 → 引擎唯一認得的兩個
_LABEL_CANON = {
    "check": "check", "checks": "check", "checking": "check",
    "check-llm": "check-llm", "check_llm": "check-llm",
    "checkllm": "check-llm", "check llm": "check-llm",
    "llm-check": "check-llm", "llm_check": "check-llm",
}
_FENCE_LABEL = re.compile(r"^```[ \t]*([A-Za-z][A-Za-z_\- ]*?)[ \t]*$")
_BARE_FENCE = re.compile(r"^```[ \t]*$")
#: 卡控動詞（有這些就確定是 ```check 區塊，與資料夾無關）
_CONTROL_VERB = re.compile(r"^\s*(?:require|applies_to|forbid):", re.MULTILINE)


def _join(lines: list[str]) -> str:
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------- 逐類修法

def _wrap_mermaid(text: str, keyword: str,
                  label: str = "") -> tuple[str, list[str]]:
    """把沒有 fence 的 mermaid 圖包進 ```mermaid（fence 外的說明文字保留）。"""
    if _FENCE in text:
        return text, []
    if "```" in text:
        return text, []          # 有其他 fence，情況不明——不猜
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(rf"^\s*(?:{keyword})\b", line):
            start = i
            break
    if start is None:
        return text, []          # 看不出是 mermaid 圖，留給 config_check 報
    body = lines[start:]
    while body and not body[-1].strip():
        body.pop()
    return (_join(lines[:start] + [_FENCE] + body + ["```"]),
            [f"包上 {_FENCE} fence（{label or keyword} 圖沒有 fence，"
             "引擎讀不到）"])


def _ensure_title(text: str, title: str) -> tuple[str, list[str]]:
    """確保檔案有 `# 標題`（沒有就補在最前面）。"""
    if _TITLE_RE.search(text):
        return text, []
    return (_join([f"# {title}", ""] + text.splitlines()),
            [f"補上標題 `# {title}`"])


def fix_erd(stem: str, text: str, rel: str = "") -> tuple[str, list[str]]:
    return _wrap_mermaid(text, "erDiagram", label="erDiagram")


def fix_flow_md(stem: str, text: str,
                rel: str = "") -> tuple[str, list[str]]:
    text, actions = _wrap_mermaid(text, "flowchart|graph",
                                  label="flowchart")
    text, more = _ensure_title(text, stem)
    return text, actions + more


def fix_table_purpose(stem: str, text: str,
                      rel: str = "") -> tuple[str, list[str]]:
    return _ensure_title(text, stem)


def fix_glossary_md(stem: str, text: str,
                    rel: str = "") -> tuple[str, list[str]]:
    """對照表沒有可辨識段落標題時，整份字典不會生效（engine 會直接報錯）。
    依**表頭關鍵字**補上段落標題——表頭寫「禁用｜改用」就補「## 禁用詞」。
    表頭看不出來的表格不動（那是語意判斷，不猜）。"""
    if _SECTION_RE.search(text):
        return text, []
    lines = text.splitlines()
    out: list[str] = []
    actions: list[str] = []
    i = 0
    while i < len(lines):
        row = _TABLE_ROW.match(lines[i])
        if not row:
            out.append(lines[i])
            i += 1
            continue
        cells = " ".join(c.strip().strip("`") for c in row.group(1).split("|"))
        heading = next((h for pattern, h in _HEADER_HINTS
                        if pattern.search(cells)), None)
        if heading:
            if out and out[-1].strip():
                out.append("")
            out += [heading, ""]
            actions.append(f"依表頭「{cells.strip()}」補上段落標題 `{heading}`"
                           "（原本整份字典不會生效）")
        while i < len(lines) and _TABLE_ROW.match(lines[i]):
            out.append(lines[i])      # 只吃連續的表格列，下一個表格各自判斷
            i += 1
    return (_join(out), actions) if actions else (text, [])


def _infer_category(stem: str) -> str:
    """檔名／id → category。既有命名慣例（naming_／structural_／bp_／ssot_）
    對得上才回傳；推不出來回空字串——不猜。"""
    name = stem.lower()
    for pattern, category in _CATEGORY_HINTS:
        if pattern.search(name):
            return category
    return ""


def _fix_fence_labels(text: str, zone: str,
                      has_control: bool) -> tuple[str, list[str]]:
    """卡控 fence 的標籤正規化。引擎只認 ```check 與 ```check-llm：

      ```checks／```check_llm／```LLM-check → 正規化成認得的標籤
      無標籤 fence 但內容是卡控動詞          → 補 ```check
      無標籤 fence 且整份還沒有任何卡控      → 依資料夾補（advisory→check-llm）

    其他語言的 fence（```sql、```yaml…）一律不碰。"""
    lines = text.splitlines()
    out: list[str] = []
    actions: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        label_match = _FENCE_LABEL.match(line)
        if label_match:
            raw = label_match.group(1)
            canon = _LABEL_CANON.get(raw.strip().lower())
            if canon and raw != canon:
                out.append(f"```{canon}")
                actions.append(f"卡控 fence 標籤 ```{raw} → ```{canon}"
                               "（引擎只認得後者）")
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if _BARE_FENCE.match(line):
            end = next((j for j in range(i + 1, len(lines))
                        if lines[j].startswith("```")), None)
            if end is not None:
                block = "\n".join(lines[i + 1:end])
                canon = ""
                if _CONTROL_VERB.search(block):
                    canon = "check"
                elif zone == "advisory" and not has_control and block.strip():
                    canon = "check-llm"
                if canon:
                    out.append(f"```{canon}")
                    actions.append(f"無標籤的卡控區塊補上 ```{canon} 標籤"
                                   "（沒有標籤的 fence 引擎讀不到卡控）")
                    i += 1
                    continue
        out.append(line)
        i += 1
    return _join(out), actions


def fix_business_md(stem: str, text: str,
                    rel: str = "") -> tuple[str, list[str]]:
    """業務素材（萬用夾）：什麼圖、什麼文字都收，只補兩件讓它讀得順的事——
    mermaid 圖沒包 fence 就包起來（否則在 GitHub／VS Code 不會渲染），
    缺 `# 標題` 就用檔名補。內容一個字都不動。"""
    text, actions = _wrap_mermaid(text, _ANY_DIAGRAM, label="mermaid")
    text, more = _ensure_title(text, stem)
    return text, actions + more


def fix_knowhow_md(stem: str, text: str, rel: str = "") -> tuple[str, list[str]]:
    """規則檔（knowhow）：補齊 front-matter 與卡控 fence 標籤。

    - `category` 缺 → 依檔名慣例推導（推不出來不補：compile 會 fail-closed 報）
    - `enforcement` 缺 → advisory 資料夾補 `advisory`；gating 資料夾補 `warning`
      （＝parser 既有預設，明寫不改變任何行為，只是把預設攤開來讓人看見）
    - 卡控 fence 標籤寫錯／沒寫 → 正規化

    不動任何已宣告的值，也不生成卡控內容——規則要檢查什麼是語意，不猜。"""
    from .skills.markdown_skill import split_front_matter

    zone = "advisory" if "/advisory/" in rel.replace(os.sep, "/") else "gating"
    try:
        meta, body = split_front_matter(text)
    except Exception:
        return text, []          # front-matter 壞掉是語意問題，交給 compile 報
    meta = meta if isinstance(meta, dict) else {}
    has_control = bool(re.search(r"```(?:check-llm|check)\s*\n", text))

    text, actions = _fix_fence_labels(text, zone, has_control)

    missing: list[tuple[str, str, str]] = []       # (欄位, 值, 說明)
    if not str(meta.get("category", "")).strip():
        inferred = _infer_category(str(meta.get("id") or stem))
        if inferred:
            missing.append(("category", inferred,
                            "依檔名推導；缺 category 會讓 compile 中斷"))
    if not str(meta.get("enforcement", "")).strip():
        value = "advisory" if zone == "advisory" else "warning"
        note = ("advisory 資料夾" if zone == "advisory"
                else "parser 既有預設；要擋請自行改 blocking")
        missing.append(("enforcement", value, note))
    if not missing:
        return text, actions

    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((j for j in range(1, len(lines))
                    if lines[j].strip() == "---"), None)
    else:
        end = None
    added = [f"{key}: {value}    # 🤖 工具補上（{note}）"
             for key, value, note in missing]
    if end is None:                                # 整份沒有 front-matter
        if not str(meta.get("id", "")).strip():
            added.insert(0, f"id: {stem}")
        lines = ["---"] + added + ["---", ""] + lines
        actions.append("補上 front-matter："
                       + "、".join(f"`{k}`" for k, _, _ in missing))
    else:
        lines = lines[:end] + added + lines[end:]
        actions.append("front-matter 補上 "
                       + "、".join(f"`{k}: {v}`" for k, v, _ in missing))
    return _join(lines), actions


_FIXERS = {"erd": fix_erd, "tables": fix_table_purpose,
           "flows": fix_flow_md, "naming": fix_glossary_md,
           "business": fix_business_md, "knowhow": fix_knowhow_md}


# ---------------------------------------------------------------- 掃描

def _folders(config_dir: str) -> list[tuple[str, str, str]]:
    """回傳 [(資料夾類型, 相對路徑, 絕對路徑)]，排序固定。"""
    out = []
    for dom in sorted(os.listdir(config_dir)):
        dom_path = os.path.join(config_dir, dom)
        if not os.path.isdir(dom_path) or dom.startswith("_"):
            continue
        for kind, rel in (("erd", "erd"), ("tables", "erd/tables"),
                          ("flows", "flows"), ("naming", "naming"),
                          ("business", "business"), ("ssot", "ssot"),
                          ("knowhow", "knowhow/gating"),
                          ("knowhow", "knowhow/advisory")):
            path = os.path.join(dom_path, *rel.split("/"))
            if os.path.isdir(path):
                out.append((kind, f"{dom}/{rel}", path))
    return out


def _entries(config_dir: str) -> list[tuple[str, str, str]]:
    """回傳 [(資料夾類型, 相對檔案路徑, 絕對檔案路徑)]（跳過 README 與子目錄）。"""
    out = []
    for kind, rel_dir, abs_dir in _folders(config_dir):
        for fn in sorted(os.listdir(abs_dir)):
            path = os.path.join(abs_dir, fn)
            if os.path.isdir(path) or fn.lower().startswith("readme") \
                    or fn.startswith("."):
                continue
            out.append((kind, f"{rel_dir}/{fn}", path))
    return out


def _rename_target(kind: str, filename: str) -> str:
    """副檔名不被載入時的正確檔名；不需要改名回空字串。"""
    if filename.endswith(_ACCEPTED.get(kind, ())):
        return ""
    for wrong, right in _RENAME.get(kind, {}).items():
        if filename.endswith(wrong):
            return filename[: -len(wrong)] + right
    return ""


# ---------------------------------------------------------------- 主流程

def run_format(config_dir: str, apply: bool = True) -> dict:
    """依資料夾路徑把 config 檔案補成引擎吃得下的格式。

    apply=False＝只看要改什麼（dry run，不寫檔）。
    回傳 {"total", "changed": [{rel, actions, renamed_to}]}。"""
    changed: list[dict] = []
    entries = _entries(config_dir)
    for kind, rel, path in entries:
        actions: list[str] = []
        filename = os.path.basename(path)
        renamed_to = ""

        target = _rename_target(kind, filename)
        if target and not os.path.exists(
                os.path.join(os.path.dirname(path), target)):
            renamed_to = target
            actions.append(f"改名為 `{target}`（原副檔名不會被引擎載入）")
            if apply:
                new_path = os.path.join(os.path.dirname(path), target)
                os.rename(path, new_path)
                path = new_path
                rel = f"{os.path.dirname(rel)}/{target}"

        fixer = _FIXERS.get(kind)
        if fixer and path.endswith(".md"):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            new_text, more = fixer(
                os.path.splitext(os.path.basename(path))[0], text, rel)
            if more and new_text != text:
                actions += more
                if apply:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_text)
        if actions:
            changed.append({"rel": rel, "actions": actions,
                            "renamed_to": renamed_to})
    return {"total": len(entries), "changed": changed}


def console_lines(summary: dict) -> list[str]:
    changed = summary["changed"]
    if not changed:
        return [f"Config 格式正規化：✅ {summary['total']} 檔格式皆正確，無需調整"]
    lines = [f"Config 格式正規化：🔧 已調整 {len(changed)}/{summary['total']} 檔"
             "（只補格式與結構，不動內容）："]
    for entry in changed:
        for action in entry["actions"]:
            lines.append(f"  🔧 config/{entry['rel']}：{action}")
    return lines
