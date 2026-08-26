# 設計素材索引 — 審閱表（自動產生，勿手改本檔）

**怎麼維護（只有三個選填欄位）**：打開想調整的素材檔，在檔案最上方加（或補）front-matter——

```yaml
---
index_summary: 一句話說明這份素材（覆蓋 🤖 自動摘要）
index_stage: [L]        # L＝logical 起草要看；P＝physical/DDL 才要看
index_required: true    # 必讀：設計出處漏引用會被提醒
---
```

不填也能用（自動摘要＋預設階段）；存檔後下次 run.py 生效。

| 素材 | 路徑 | 摘要 | 階段 | 必讀 | 狀態 |
|---|---|---|---|---|---|
| 參考 ER 模型 | `config/Common/erd/_sample.md` | 實體：sample_child、sample_parent | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/Common/naming/glossary.md` | 禁用 9、別名 6、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/Common/ssot/registry.yaml` | 權威登錄：customer、product | L,P | ✅ | 🤖 自動（待人工確認） |
| 正式區資產 | `config/Common/production/registry.md` | 正式區已核准 2 個 data subject、3 張表——設計新表前先讀，能複用就不要重造 | L,P | ✅ | ✍️ 已人工維護 |
| 產品縮寫註冊表 | `config/Common/products/registry.md` | （尚無產品，含分層前綴定義） | P | — | 🤖 自動（待人工確認） |
| 參考 ER 模型 | `config/BLM/erd/blm_core.md` | 實體：blm_detail、blm_master | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/BLM/naming/glossary.md` | 禁用 0、別名 0、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/BLM/ssot/registry.yaml` | （空登錄） | L,P | ✅ | 🤖 自動（待人工確認） |
| 參考 ER 模型 | `config/CRM/erd/crm_core.md` | 實體：dim_customer、order_items、orders | L | — | 🤖 自動（待人工確認） |
| 參考表用途 | `config/CRM/erd/tables/dim_customer.md` | 客戶主檔維度表。一列代表一位客戶，客戶屬性（名稱、分級、聯絡方式）的 | L | — | 🤖 自動（待人工確認） |
| 參考表用途 | `config/CRM/erd/tables/order_items.md` | 訂單明細事實表。一列代表訂單內的一個品項（訂單 × 商品粒度）， | L | — | 🤖 自動（待人工確認） |
| 參考表用途 | `config/CRM/erd/tables/orders.md` | 訂單頭事實表。一列代表一張已成立的訂單，承載訂單層級的業務事實 | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/CRM/naming/glossary.md` | 禁用 0、別名 0、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| E2E 業務流程 | `config/CRM/flows/order_to_revenue.md` | 結帳服務寫入訂單，展開明細，匯總成營收報表。 | L | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/CRM/ssot/registry.yaml` | （空登錄） | L,P | ✅ | 🤖 自動（待人工確認） |
| 產品縮寫註冊表 | `config/CRM/products/registry.md` | 產品：pi、om | P | — | 🤖 自動（待人工確認） |
| 參考 ER 模型 | `config/FCM/erd/fcm_core.md` | 實體：fcm_detail、fcm_master | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/FCM/naming/glossary.md` | 禁用 0、別名 0、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/FCM/ssot/registry.yaml` | （空登錄） | L,P | ✅ | 🤖 自動（待人工確認） |
| 參考 ER 模型 | `config/PLM/erd/plm_core.md` | 實體：bom、bom_line、part_master | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/PLM/naming/glossary.md` | 禁用 0、別名 0、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| E2E 業務流程 | `config/PLM/flows/eco_to_bom.md` | 變更單核准後更新料件版次並展開至 BOM。（範例，依實際流程替換） | L | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/PLM/ssot/registry.yaml` | （空登錄） | L,P | ✅ | 🤖 自動（待人工確認） |
| 參考 ER 模型 | `config/SCM/erd/scm_core.md` | 實體：purchase_order、purchase_order_line、supplier | L | — | 🤖 自動（待人工確認） |
| 詞彙字典 | `config/SCM/naming/glossary.md` | 禁用 0、別名 0、白名單未啟用 | P | — | 🤖 自動（待人工確認） |
| E2E 業務流程 | `config/SCM/flows/procure_to_pay.md` | 供應商主檔支撐採購單，採購單對應付款。（範例，依實際流程替換） | L | — | 🤖 自動（待人工確認） |
| SSOT 權威登錄 | `config/SCM/ssot/registry.yaml` | （空登錄） | L,P | ✅ | 🤖 自動（待人工確認） |

共 27 份素材。🤖 表示摘要為自動萃取——有空逐條補 front-matter 即可，一次補幾條都行。
