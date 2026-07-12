CREATE TABLE standalone_metric (
    metric_key  String COMMENT '指標唯一識別',
    metric_name String COMMENT '指標名稱',
    created_at  DateTime('UTC') COMMENT '建立時間',
    updated_at  DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (metric_key);
