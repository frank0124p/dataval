CREATE TABLE customer_er_source (
    customer_id UInt64 COMMENT '客戶唯一識別',
    created_at  DateTime('UTC') COMMENT '建立時間',
    updated_at  DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (customer_id);

CREATE TABLE order_er_event (
    order_id    UInt64 COMMENT '訂單唯一識別',
    customer_id UInt64 COMMENT '下單客戶識別',
    created_at  DateTime('UTC') COMMENT '建立時間',
    updated_at  DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (order_id);
