# products/ — 產品縮寫註冊表（維護指南與 template）

Product suite（domain）底下的**產品**縮寫在這裡登錄。data subject 在
`context.md` front-matter 宣告 `product: <縮寫>` 後，design mode 會：

1. 把表命名前綴規則帶進設計 prompt：表名格式 **`<分層前綴>_<產品縮寫>_<語意名>`**
   （例：`dim_pi_customer`、`dwd_om_order`）
2. 逐表**確定性檢查**產品前綴（結果渲染在 physical design 的
   「表名產品前綴檢查」）
3. 未登錄的縮寫會被提示，並引導在設計問答提議登錄

## 檔案規則

- 本資料夾任意檔名的 `.md` 都會被讀取（`README*` 除外）
- **Common 放全公司共用**（分層前綴通常放這）；`config/<域>/products/`
  放該 domain 的產品縮寫，**與 Common 合併**（同縮寫 domain 覆蓋 Common）
- 段落標題以關鍵字辨識：含「產品／product」→ 產品縮寫表；
  含「分層／layer／前綴」→ 分層前綴表

## Template（新增檔案時複製）

```markdown
# <域> 產品縮寫

## 產品縮寫
| 縮寫 | 產品名稱 | 說明 |
|---|---|---|
| pi | Product Insight | 產品洞察 |
| om | Order Management | 訂單管理 |

## 分層前綴
| 前綴 | 層級 | 說明 |
|---|---|---|
| ods | 原始層 | 貼源不加工 |
| dim | 維度表 | 主資料／參照 |
| dwd | 明細事實 | 一行一業務事件 |
| dws | 彙總層 | 預聚合 |
| ads | 應用層 | 面向特定應用的寬表 |
```

## 維護語意

- **縮寫一律小寫**、2–4 字元為宜；表名比對不分大小寫
- 產品下線不要刪列，於說明欄註明「已停用」（歷史表名仍要能對照）
- 分層前綴是命名**形式**的一部分，與詞彙字典（naming/）的**用詞**規範
  互補：`dim_pi_customer` 的 `customer` 仍須遵守詞彙字典
- 編輯後下次 `run.py` 立即生效（知識輸入，每輪重新載入）
