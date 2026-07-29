# PLM 領域核心參考模型（範例）

```mermaid
erDiagram
    part_master ||--o{ bom : "料件被 BOM 引用"
    bom ||--o{ bom_line : "BOM 展開子件"
```
