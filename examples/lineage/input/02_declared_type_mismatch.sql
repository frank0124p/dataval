CREATE TABLE customer_export (
    export_id      UInt64 COMMENT '匯出批次唯一識別',
    customer_id    String COMMENT '刻意使用錯誤型別的客戶識別',
    created_at     DateTime('UTC') COMMENT '建立時間',
    updated_at     DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (export_id);
