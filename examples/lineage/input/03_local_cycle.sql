CREATE TABLE staged_order (
    order_id   UInt64 COMMENT '訂單唯一識別',
    created_at DateTime('UTC') COMMENT '建立時間',
    updated_at DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (order_id);

CREATE TABLE order_summary (
    order_id   UInt64 COMMENT '訂單唯一識別',
    created_at DateTime('UTC') COMMENT '建立時間',
    updated_at DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (order_id);
