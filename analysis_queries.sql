-- ============================================================
-- Retail Supply Chain Intelligence — SQL Analysis Queries
-- Database: MySQL  |  Dataset: Olist E-Commerce
-- Author:   Ashraf Bukhari
-- ============================================================


-- ── QUERY 1: Monthly Revenue & Order Count Trend ──────────────────────────
SELECT
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')  AS month,
    COUNT(DISTINCT o.order_id)                         AS total_orders,
    ROUND(SUM(oi.price), 2)                            AS total_revenue,
    ROUND(AVG(oi.price), 2)                            AS avg_order_value,
    ROUND(SUM(oi.freight_value), 2)                    AS total_freight
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY month
ORDER BY month;


-- ── QUERY 2: Top 10 Categories by Revenue ─────────────────────────────────
SELECT
    t.product_category_name_english                    AS category,
    COUNT(DISTINCT oi.order_id)                        AS orders,
    ROUND(SUM(oi.price), 2)                            AS revenue,
    ROUND(AVG(oi.price), 2)                            AS avg_price,
    ROUND(AVG(r.review_score), 2)                      AS avg_review_score
FROM order_items oi
JOIN products p             ON oi.product_id = p.product_id
JOIN product_category_name_translation t
                            ON p.product_category_name = t.product_category_name
LEFT JOIN order_reviews r   ON oi.order_id = r.order_id
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;


-- ── QUERY 3: Late Delivery Rate by Customer State ─────────────────────────
SELECT
    c.customer_state,
    COUNT(*)                                           AS total_orders,
    SUM(CASE
            WHEN o.order_delivered_customer_date
                 > o.order_estimated_delivery_date
            THEN 1 ELSE 0
        END)                                           AS late_orders,
    ROUND(
        100.0 * SUM(CASE
                        WHEN o.order_delivered_customer_date
                             > o.order_estimated_delivery_date
                        THEN 1 ELSE 0
                    END) / COUNT(*), 2)                AS late_rate_pct,
    ROUND(AVG(DATEDIFF(
        o.order_delivered_customer_date,
        o.order_purchase_timestamp)), 1)               AS avg_delivery_days
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(*) >= 100
ORDER BY late_rate_pct DESC;


-- ── QUERY 4: Review Score vs Delivery Timeliness ─────────────────────────
SELECT
    CASE
        WHEN o.order_delivered_customer_date
             > o.order_estimated_delivery_date THEN 'Late'
        ELSE 'On Time'
    END                                                AS delivery_status,
    COUNT(*)                                           AS orders,
    ROUND(AVG(r.review_score), 3)                      AS avg_review_score,
    SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) AS five_star_count,
    SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) AS low_score_count
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_status;


-- ── QUERY 5: Seller Performance Ranking (Health Score) ────────────────────
SELECT
    s.seller_id,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)                        AS total_orders,
    ROUND(SUM(oi.price), 2)                            AS total_revenue,
    ROUND(AVG(r.review_score), 2)                      AS avg_review,
    ROUND(100.0 * SUM(CASE
        WHEN o.order_delivered_customer_date
             > o.order_estimated_delivery_date THEN 1 ELSE 0
        END) / COUNT(*), 2)                            AS late_rate_pct,
    -- Composite Seller Health Score (0–100)
    ROUND(
        (AVG(r.review_score) / 5.0) * 40
      + (1 - SUM(CASE
                    WHEN o.order_delivered_customer_date
                         > o.order_estimated_delivery_date THEN 1 ELSE 0
                 END) / COUNT(*)) * 40
      + LEAST(COUNT(DISTINCT oi.order_id) / 500.0, 1) * 20
    , 1)                                               AS health_score
FROM sellers s
JOIN order_items oi ON s.seller_id = oi.seller_id
JOIN orders o       ON oi.order_id = o.order_id
LEFT JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY s.seller_id, s.seller_state
HAVING total_orders >= 10
ORDER BY health_score DESC
LIMIT 20;


-- ── QUERY 6: Payment Method Breakdown by Revenue ──────────────────────────
SELECT
    p.payment_type,
    COUNT(*)                                           AS transactions,
    ROUND(SUM(p.payment_value), 2)                     AS total_value,
    ROUND(AVG(p.payment_value), 2)                     AS avg_value,
    ROUND(AVG(p.payment_installments), 1)              AS avg_installments
FROM order_payments p
JOIN orders o ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY p.payment_type
ORDER BY total_value DESC;


-- ── QUERY 7: Peak Order Hours & Days ──────────────────────────────────────
SELECT
    DAYNAME(order_purchase_timestamp)                  AS day_name,
    HOUR(order_purchase_timestamp)                     AS hour_of_day,
    COUNT(*)                                           AS order_count
FROM orders
WHERE order_status = 'delivered'
GROUP BY day_name, hour_of_day
ORDER BY order_count DESC
LIMIT 20;


-- ── QUERY 8: Revenue Contribution — Top 20% Sellers (Pareto) ──────────────
WITH seller_rev AS (
    SELECT
        s.seller_id,
        ROUND(SUM(oi.price), 2) AS revenue
    FROM sellers s
    JOIN order_items oi ON s.seller_id = oi.seller_id
    JOIN orders o       ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY s.seller_id
),
ranked AS (
    SELECT
        seller_id, revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC)      AS rnk,
        COUNT(*) OVER ()                               AS total_sellers,
        SUM(revenue) OVER ()                           AS total_revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC)      AS cumulative_revenue
    FROM seller_rev
)
SELECT
    rnk, seller_id, revenue,
    ROUND(100.0 * rnk / total_sellers, 1)             AS pct_of_sellers,
    ROUND(100.0 * cumulative_revenue / total_revenue, 1) AS pct_of_revenue
FROM ranked
WHERE rnk <= 20
ORDER BY rnk;


-- ── QUERY 9: Month-over-Month Revenue Growth (Window Function) ─────────────
WITH monthly_rev AS (
    SELECT
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
        ROUND(SUM(oi.price), 2)                          AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY month
)
SELECT
    month,
    revenue,
    LAG(revenue)  OVER (ORDER BY month)                AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1)
                                                       AS mom_growth_pct,
    ROUND(AVG(revenue) OVER (
        ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                                                       AS rolling_3m_avg
FROM monthly_rev
ORDER BY month;


-- ── QUERY 10: RFM Scoring per Customer ────────────────────────────────────
WITH rfm_raw AS (
    SELECT
        c.customer_unique_id,
        DATEDIFF('2018-12-01', MAX(o.order_purchase_timestamp)) AS recency_days,
        COUNT(DISTINCT o.order_id)                              AS frequency,
        ROUND(SUM(oi.price), 2)                                 AS monetary
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    NTILE(4) OVER (ORDER BY recency_days DESC)  AS R_score,
    NTILE(4) OVER (ORDER BY frequency)          AS F_score,
    NTILE(4) OVER (ORDER BY monetary)           AS M_score,
    NTILE(4) OVER (ORDER BY recency_days DESC)
  + NTILE(4) OVER (ORDER BY frequency)
  + NTILE(4) OVER (ORDER BY monetary)           AS rfm_total
FROM rfm_raw
ORDER BY rfm_total DESC
LIMIT 50;
