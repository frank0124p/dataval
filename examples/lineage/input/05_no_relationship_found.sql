CREATE TABLE audit_log (
    log_key    String COMMENT '日誌唯一識別',
    message    String COMMENT '日誌內容',
    created_at DateTime('UTC') COMMENT '建立時間',
    updated_at DateTime('UTC') COMMENT '更新時間'
) ENGINE = MergeTree() ORDER BY (log_key);
