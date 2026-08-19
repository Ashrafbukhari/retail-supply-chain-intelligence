"""
02_cleaning.py  —  Data Cleaning & Master DataFrame Builder
Loads all 8 tables, cleans them, joins into one master file.
Fixed for real Olist dataset (handles null product categories).
"""

import pandas as pd
import numpy as np
import os, warnings
warnings.filterwarnings("ignore")

RAW  = "data/raw"
PROC = "data/processed"
os.makedirs(PROC, exist_ok=True)

print("=" * 60)
print("STEP 1 — Loading raw tables")
print("=" * 60)

orders   = pd.read_csv(f"{RAW}/olist_orders_dataset.csv")
items    = pd.read_csv(f"{RAW}/olist_order_items_dataset.csv")
payments = pd.read_csv(f"{RAW}/olist_order_payments_dataset.csv")
reviews  = pd.read_csv(f"{RAW}/olist_order_reviews_dataset.csv")
customers= pd.read_csv(f"{RAW}/olist_customers_dataset.csv")
sellers  = pd.read_csv(f"{RAW}/olist_sellers_dataset.csv")
products = pd.read_csv(f"{RAW}/olist_products_dataset.csv")
transl   = pd.read_csv(f"{RAW}/product_category_name_translation.csv")

print(f"  orders:    {len(orders):>10,} rows")
print(f"  items:     {len(items):>10,} rows")
print(f"  payments:  {len(payments):>10,} rows")
print(f"  reviews:   {len(reviews):>10,} rows")
print(f"  customers: {len(customers):>10,} rows")
print(f"  sellers:   {len(sellers):>10,} rows")
print(f"  products:  {len(products):>10,} rows")

print("\n" + "=" * 60)
print("STEP 2 — Cleaning: Date columns")
print("=" * 60)

date_cols = ["order_purchase_timestamp",
             "order_delivered_customer_date",
             "order_estimated_delivery_date"]

for col in date_cols:
    if col in orders.columns:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

print(f"  Date nulls after parse: {orders[date_cols].isnull().sum().to_dict()}")

print("\n" + "=" * 60)
print("STEP 3 — Cleaning: Duplicates & nulls")
print("=" * 60)

before = len(orders)
orders.drop_duplicates(subset=["order_id"], inplace=True)
print(f"  Duplicate orders removed: {before - len(orders)}")

before = len(items)
items.drop_duplicates(subset=["order_id","order_item_id"], inplace=True)
print(f"  Duplicate items removed:  {before - len(items)}")

# Clip extreme prices (data quality)
p01, p99 = items["price"].quantile(0.01), items["price"].quantile(0.99)
items["price"] = items["price"].clip(p01, p99)
print(f"  Price range after clip:  ₹{p01:.2f} – ₹{p99:.2f}")

print("\n" + "=" * 60)
print("STEP 4 — Feature Engineering")
print("=" * 60)

# Delivered orders only for delivery analysis
delivered = orders[orders["order_status"] == "delivered"].copy()
delivered["delivery_days"] = (
    delivered["order_delivered_customer_date"] -
    delivered["order_purchase_timestamp"]
).dt.days

delivered["is_late"] = (
    delivered["order_delivered_customer_date"] >
    delivered["order_estimated_delivery_date"]
)

delivered["month"]   = delivered["order_purchase_timestamp"].dt.to_period("M")
delivered["year"]    = delivered["order_purchase_timestamp"].dt.year
delivered["weekday"] = delivered["order_purchase_timestamp"].dt.day_name()
delivered["hour"]    = delivered["order_purchase_timestamp"].dt.hour

print(f"  Delivered orders: {len(delivered):,}")
print(f"  Late orders:      {delivered['is_late'].sum():,}  ({delivered['is_late'].mean()*100:.1f}%)")
print(f"  Avg delivery:     {delivered['delivery_days'].mean():.1f} days")

print("\n" + "=" * 60)
print("STEP 5 — Building Master DataFrame")
print("=" * 60)

# ── Order-level revenue ───────────────────────────────────────────────────
order_revenue = items.groupby("order_id").agg(
    total_price   = ("price",         "sum"),
    total_freight = ("freight_value", "sum"),
    item_count    = ("order_item_id", "count"),
).reset_index()
order_revenue["total_value"] = order_revenue["total_price"] + order_revenue["total_freight"]

# ── Category per order ────────────────────────────────────────────────────
# FIX: use .dropna() before value_counts() to handle products with no category
# and fall back to "unknown" when an order has no category at all

if "category" in items.columns:
    # synthetic data path (category column exists directly on items)
    order_cat = items.groupby("order_id")["category"].agg(
        lambda x: x.dropna().value_counts().index[0]
        if len(x.dropna()) > 0 else "unknown"
    ).reset_index()
    order_cat.columns = ["order_id", "main_category"]

else:
    # real Olist path — join products table to get category name
    items_with_cat = items.merge(
        products[["product_id", "product_category_name"]],
        on="product_id",
        how="left"
    )
    order_cat = items_with_cat.groupby("order_id")["product_category_name"].agg(
        lambda x: x.dropna().value_counts().index[0]
        if len(x.dropna()) > 0 else "unknown"
    ).reset_index()
    order_cat.columns = ["order_id", "main_category"]

# ── Primary seller per order ──────────────────────────────────────────────
order_seller = items.groupby("order_id")["seller_id"].first().reset_index()

# ── Payments — deduplicate to one row per order ───────────────────────────
# Real Olist has multiple payment rows per order (split payments / installments)
# Keep the row with the highest payment_value as the "primary" payment
payments_dedup = (
    payments
    .sort_values("payment_value", ascending=False)
    .drop_duplicates(subset=["order_id"], keep="first")
    [["order_id", "payment_type", "payment_installments", "payment_value"]]
)

# ── Reviews — deduplicate to one row per order ────────────────────────────
# Some orders have multiple reviews; keep the most recent one
reviews_dedup = (
    reviews
    .drop_duplicates(subset=["order_id"], keep="last")
    [["order_id", "review_score"]]
)

# ── Sellers — rename state column to avoid clash with customer_state ───────
sellers_renamed = sellers.rename(columns={"seller_state": "seller_state"})

# ── Merge everything into master ──────────────────────────────────────────
master = (
    delivered
    .merge(order_revenue,    on="order_id",    how="left")
    .merge(order_cat,        on="order_id",    how="left")
    .merge(order_seller,     on="order_id",    how="left")
    .merge(payments_dedup,   on="order_id",    how="left")
    .merge(reviews_dedup,    on="order_id",    how="left")
    .merge(customers,        on="customer_id", how="left")
    .merge(sellers_renamed,  on="seller_id",   how="left")
)

# ── Category English name ─────────────────────────────────────────────────
cat_map = dict(zip(
    transl["product_category_name"],
    transl["product_category_name_english"]
))
master["category_english"] = (
    master["main_category"]
    .map(cat_map)
    .fillna(master["main_category"].str.replace("_", " ").str.title())
)

# ── Delivery delay in hours ───────────────────────────────────────────────
master["delay_hours"] = (
    master["order_delivered_customer_date"] -
    master["order_estimated_delivery_date"]
).dt.total_seconds() / 3600

# ── Save outputs ──────────────────────────────────────────────────────────
master.to_csv(f"{PROC}/master.csv", index=False)
print(f"  Master DataFrame: {master.shape[0]:,} rows × {master.shape[1]} columns")
print(f"  Saved → data/processed/master.csv")

delivered.to_csv(f"{PROC}/delivered_orders.csv", index=False)
items.to_csv(f"{PROC}/items_clean.csv", index=False)

print("\n✅ Cleaning complete.")
