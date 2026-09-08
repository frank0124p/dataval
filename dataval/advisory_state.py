"""顧問區重跑判定 — 「這輪還需要動用 LLM 嗎？」

`run.py` 是零 LLM 的，語意建議要靠 agent 的 LLM 補。問題是：input 一個字
沒改、規則也沒動的重跑，agent 照樣被叫去重讀 ~24K 字元的 prompt、重寫一份
內容幾乎一樣的建議——那是整條流程最貴的一步，卻完全沒有產生新資訊。

判定方式很直接：**prompt 本身就是最好的指紋**。`advisory_prompt.md` 是由
schema、context、findings、已澄清事項、素材索引確定性組出來的——只要其中
任何一項變了，prompt 的位元組就會變。所以：

    prompt 位元組相同 ＋ 上次的 advisory_result 還在且沒被改過
        → 顧問區可以直接沿用，跳過 LLM，只要跑 merge_advisory.py

merge_advisory.py 合併成功時寫下 stamp（prompt 與 result 的 sha256），
run.py 下次比對。比對不過就照舊要求重補——保守的一邊是「重做」，
不會拿舊建議去搭新報告。

零 LLM、零網路、純檔案比對。
"""
from __future__ import annotations

import hashlib
import json
import os

#: stamp 檔名後綴。放 govern_doc/<名>/，與其他產物同一個家。
STAMP_SUFFIX = ".advisory_state.json"
STAMP_VERSION = 1


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except Exception:
        return ""


def stamp_path(govern_dir: str, name: str) -> str:
    return os.path.join(govern_dir, name + STAMP_SUFFIX)


def prompt_path(govern_dir: str, name: str) -> str:
    return os.path.join(govern_dir, name + ".advisory_prompt.md")


def result_path(govern_dir: str, name: str) -> str:
    return os.path.join(govern_dir, name + ".advisory_result.json")


def write_stamp(govern_dir: str, name: str, prompt: str) -> None:
    """merge_advisory.py 合併成功後呼叫：記下這份建議是依據哪份 prompt 做的。"""
    payload = {
        "version": STAMP_VERSION,
        "prompt_sha256": sha(prompt),
        "result_sha256": sha(_read(result_path(govern_dir, name))),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"
    path = stamp_path(govern_dir, name)
    if _read(path) != body:            # 寫入前先比對，維持位元組穩定
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)


def reusable(govern_dir: str, name: str, prompt: str) -> tuple[bool, str]:
    """這輪的顧問區能不能沿用上次的結果？回傳 (可沿用, 原因)。

    任何一項對不上就回 False——寧可多跑一次 LLM，也不要拿舊建議搭新報告。"""
    result_file = result_path(govern_dir, name)
    if not os.path.isfile(result_file):
        return False, "尚無 advisory_result.json"
    try:
        with open(stamp_path(govern_dir, name), encoding="utf-8") as handle:
            state = json.load(handle)
    except Exception:
        return False, "尚無合併紀錄（advisory_state.json）"
    if state.get("version") != STAMP_VERSION:
        return False, "合併紀錄格式已更新"
    if state.get("prompt_sha256") != sha(prompt):
        return False, "prompt 已變（schema／情境／findings／已澄清事項有變動）"
    if state.get("result_sha256") != sha(_read(result_file)):
        return False, "advisory_result.json 已被改動"
    return True, "prompt 與上次完全相同"
