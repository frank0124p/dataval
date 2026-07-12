CREATE TABLE customer_snapshot (
    snapshot_id    UInt64 COMMENT '快照唯一識別',
    customer_id    UInt64 COMMENT '客戶唯一識別',
    created_at     DateTime('UTC') COMMENT '建立時間',
    updated_at     DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (snapshot_id);
