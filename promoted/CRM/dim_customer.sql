-- 正式區：CRM 已認可的客戶主檔（權威命名基準）
CREATE TABLE dim_customer (
    customer_id   UInt64  COMMENT '客戶唯一識別',
    customer_name String  COMMENT '客戶名稱',
    customer_email String COMMENT '客戶電子郵件',
    created_at    DateTime COMMENT '建立時間',
    updated_at    DateTime COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (customer_id);
