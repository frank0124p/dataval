# E2E 流程（Markdown ＋ ```mermaid flowchart）

描述資料從來源到消費端的端到端流程。標準格式是 **Markdown**：
`flows/<流程名>.md`——第一個 `# 標題` 是流程名稱，flowchart 放
```mermaid fence 內。**節點名對得上本次 DDL 的表就是表站點**，
其餘自然是外部站點（來源系統、報表），不需要標 kind。

````markdown
# 訂單到營收
結帳服務寫入訂單，展開明細，匯總成營收報表。

```mermaid
flowchart LR
  結帳服務 --> orders --> order_items --> 營收日報
```
````

- 支援分支圖（不限一直線）：上下游以圖的前驅／後繼計算
- 節點可用 `id[顯示名]` 等 mermaid 形狀；連線用 `-->`（可帶 `|標籤|`）
- 舊式 `*.flow.yaml`（stages ＋ kind）仍相容

驗證 DDL 時，表若出現在流程中，報告會標註它的站點與上下游
（FLOW.CONTEXT，資訊不擋）；流程檔格式錯誤會以 FLOW.SPEC 提醒。
