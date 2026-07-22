# E2E 流程(`*.flow.yaml`)

描述資料從來源到消費端的端到端流程。推薦格式 YAML:結構簡單、可註解、
可被程式驗證(Mermaid 適合畫關係,流程需要「有序站點+屬性」,YAML 更合適)。

```yaml
flow: order_to_revenue      # 流程代號
title: 訂單到營收            # 顯示名稱
description: 一句話說明
stages:                     # 依序站點;kind: source | table | report
  - name: 結帳服務
    kind: source
  - name: orders            # kind=table 時 name 必須是表名
    kind: table
  - name: 營收日報
    kind: report
```

驗證 DDL 時,表若出現在流程中,報告會標註它的站點與上下游(FLOW.CONTEXT,
資訊不擋);流程檔格式錯誤會以 FLOW.SPEC 提醒。
