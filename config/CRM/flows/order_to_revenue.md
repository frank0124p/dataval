# 訂單到營收
結帳服務寫入訂單，展開明細，匯總成營收報表。

```mermaid
flowchart LR
  結帳服務 --> orders --> order_items --> 營收日報
```
