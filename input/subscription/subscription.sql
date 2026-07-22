-- New data subject: subscription, joining across CRM + billing domains.
CREATE TABLE dim_customer (
    customer_id   UInt64,
    customer_name String,
    customer_email String,
    customer_tier String,
    created_at    DateTime,
    updated_at    DateTime
) ENGINE = MergeTree() ORDER BY (customer_id);

CREATE TABLE subscription (
    subscription_id UInt64,
    customer_id     String,                 -- TYPE MISMATCH vs dim_customer.customer_id
    customer_email  String,                 -- SSOT: duplicates dim_customer's owned attr
    MonthlyPrice    Float64,                 -- naming (camelCase) + money-as-float
    started_at      DateTime,
    created_at      DateTime
) ENGINE = MergeTree() ORDER BY (subscription_id);

CREATE TABLE billing_event (
    event_id     UInt64,
    customer_id  UInt64,
    amount       Float64,                    -- money-as-float
    occurred_at  DateTime64(3)
) ENGINE = MergeTree() ORDER BY (event_id);
