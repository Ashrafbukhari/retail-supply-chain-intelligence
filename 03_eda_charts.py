"""
03_eda_charts.py  —  Full EDA + Visualization
Generates 10 professional charts saved to outputs/charts/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings, os
warnings.filterwarnings("ignore")

PROC    = "data/processed"
CHARTS  = "outputs/charts"
os.makedirs(CHARTS, exist_ok=True)

# ── Style ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "figure.dpi":       130,
    "axes.titlesize":   13,
    "axes.labelsize":   11,
})
BLUE   = "#1A56A0"
ORANGE = "#F97316"
GREEN  = "#16A34A"
RED    = "#DC2626"
PURPLE = "#7C3AED"
COLORS = [BLUE, ORANGE, GREEN, RED, PURPLE, "#0891B2", "#CA8A04", "#DB2777"]

master = pd.read_csv(f"{PROC}/master.csv", parse_dates=["order_purchase_timestamp"])
items  = pd.read_csv(f"{PROC}/items_clean.csv")

print(f"Master loaded: {master.shape}")

# ════════════════════════════════════════════════════════════════════════════
# CHART 1 — Monthly Revenue Trend with Annotations
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 1: Monthly Revenue Trend...")

monthly = master.groupby(master["order_purchase_timestamp"].dt.to_period("M")).agg(
    revenue     = ("total_price", "sum"),
    orders      = ("order_id",    "count"),
    avg_order   = ("total_price", "mean"),
).reset_index()
monthly["month_dt"] = monthly["order_purchase_timestamp"].dt.to_timestamp()
monthly["revenue_k"] = monthly["revenue"] / 1000

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
fig.suptitle("Monthly Revenue & Order Volume — 2017 to 2018", fontsize=15, fontweight="bold", y=0.98)

# Revenue line
ax1.fill_between(monthly["month_dt"], monthly["revenue_k"], alpha=0.15, color=BLUE)
ax1.plot(monthly["month_dt"], monthly["revenue_k"], color=BLUE, linewidth=2.5, marker="o", markersize=4)
ax1.set_ylabel("Revenue (₹ Thousands)", color=BLUE)

# Annotate peak
peak_idx = monthly["revenue_k"].idxmax()
ax1.annotate(f'Peak\n₹{monthly.loc[peak_idx,"revenue_k"]:.0f}K',
    xy=(monthly.loc[peak_idx,"month_dt"], monthly.loc[peak_idx,"revenue_k"]),
    xytext=(0, 20), textcoords="offset points", fontsize=9,
    color=BLUE, fontweight="bold", ha="center",
    arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.2))

# Growth label
start_rev = monthly["revenue_k"].iloc[0]
end_rev   = monthly["revenue_k"].iloc[-3]
growth    = (end_rev - start_rev) / start_rev * 100
ax1.text(0.02, 0.88, f"Growth Jan'17→Aug'18: +{growth:.0f}%",
         transform=ax1.transAxes, fontsize=10, color=GREEN,
         bbox=dict(boxstyle="round,pad=0.3", facecolor="#D1FAE5", alpha=0.8))

# Order volume bars
ax2.bar(monthly["month_dt"], monthly["orders"], color=ORANGE, alpha=0.75, width=20)
ax2.set_ylabel("Number of Orders", color=ORANGE)
ax2.set_xlabel("Month")

plt.tight_layout()
plt.savefig(f"{CHARTS}/01_monthly_revenue_trend.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 1 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 2 — Top 10 Categories by Revenue
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 2: Category Revenue...")

cat_rev = master.groupby("category_english").agg(
    revenue  = ("total_price","sum"),
    orders   = ("order_id","count"),
    avg_rev  = ("total_price","mean"),
    avg_score= ("review_score","mean"),
).reset_index().sort_values("revenue", ascending=False).head(10)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(cat_rev["category_english"][::-1],
               cat_rev["revenue"][::-1] / 1000,
               color=[BLUE if i < 3 else "#93C5FD" for i in range(9,-1,-1)],
               edgecolor="white", height=0.65)

for i, (val, score) in enumerate(zip(cat_rev["revenue"][::-1]/1000,
                                      cat_rev["avg_score"][::-1])):
    ax.text(val + 5, i, f"₹{val:.0f}K  ★{score:.1f}", va="center", fontsize=9.5)

ax.set_xlabel("Total Revenue (₹ Thousands)")
ax.set_title("Top 10 Product Categories by Revenue", fontsize=14, fontweight="bold")
ax.set_xlim(0, cat_rev["revenue"].max()/1000 * 1.22)
fig.tight_layout()
plt.savefig(f"{CHARTS}/02_category_revenue.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 2 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 3 — Late Delivery Rate by State (heatmap-style bar)
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 3: Delivery Performance by State...")

state_del = master.groupby("customer_state").agg(
    orders     = ("order_id", "count"),
    late_rate  = ("is_late",  "mean"),
    avg_days   = ("delivery_days", "mean"),
    avg_score  = ("review_score",  "mean"),
).reset_index()
state_del["late_pct"] = state_del["late_rate"] * 100
state_del = state_del[state_del["orders"] >= 100].sort_values("late_pct", ascending=True)

fig, ax = plt.subplots(figsize=(12, 7))
colors_bar = [RED if v > 15 else ORANGE if v > 10 else GREEN
              for v in state_del["late_pct"]]
ax.barh(state_del["customer_state"], state_del["late_pct"],
        color=colors_bar, edgecolor="white", height=0.7)
for i, (v, d, s) in enumerate(zip(state_del["late_pct"],
                                   state_del["avg_days"],
                                   state_del["avg_score"])):
    ax.text(v + 0.3, i, f"{v:.1f}%  |  {d:.0f} days  |  ★{s:.1f}",
            va="center", fontsize=8.5)

ax.set_xlabel("Late Delivery Rate (%)")
ax.set_title("Late Delivery Rate, Avg Days & Review Score by Customer State",
             fontsize=13, fontweight="bold")
ax.axvline(state_del["late_pct"].mean(), color=BLUE, linestyle="--",
           alpha=0.6, label=f"Average: {state_del['late_pct'].mean():.1f}%")
ax.legend(fontsize=9)
patches = [mpatches.Patch(color=GREEN, label="<10% late"),
           mpatches.Patch(color=ORANGE, label="10–15% late"),
           mpatches.Patch(color=RED, label=">15% late")]
ax.legend(handles=patches, loc="lower right", fontsize=9)
fig.tight_layout()
plt.savefig(f"{CHARTS}/03_delivery_by_state.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 3 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 4 — Delivery Delay vs Review Score (Correlation)
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 4: Delay vs Review Score...")

corr_data = master[["delivery_days","review_score","is_late"]].dropna()
correlation = corr_data["delivery_days"].corr(corr_data["review_score"])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle(f"Delivery Delay vs Customer Satisfaction  (r = {correlation:.2f})",
             fontsize=14, fontweight="bold")

# Scatter
sample = corr_data.sample(min(3000, len(corr_data)), random_state=42)
colors_s = [RED if late else GREEN for late in sample["is_late"]]
ax1.scatter(sample["delivery_days"], sample["review_score"] + np.random.normal(0,0.08,len(sample)),
            c=colors_s, alpha=0.25, s=12)
# Trend line
z = np.polyfit(sample["delivery_days"].dropna(), sample["review_score"].dropna(), 1)
p = np.poly1d(z)
x_line = np.linspace(sample["delivery_days"].min(), sample["delivery_days"].max(), 100)
ax1.plot(x_line, p(x_line), color=BLUE, linewidth=2.5, linestyle="--")
ax1.set_xlabel("Delivery Days"); ax1.set_ylabel("Review Score")
ax1.set_title("Scatter: Delivery Days vs Review Score")
late_p  = mpatches.Patch(color=RED,   label="Late delivery")
ontime_p= mpatches.Patch(color=GREEN, label="On-time delivery")
ax1.legend(handles=[late_p, ontime_p], fontsize=9)

# Box: review score by late/ontime
on_time_scores = corr_data[~corr_data["is_late"]]["review_score"]
late_scores    = corr_data[ corr_data["is_late"]]["review_score"]
ax2.boxplot([on_time_scores, late_scores], labels=["On-Time", "Late"],
            patch_artist=True,
            boxprops=dict(facecolor="#DBEAFE"),
            medianprops=dict(color=RED, linewidth=2))
ax2.set_ylabel("Review Score")
ax2.set_title(f"Review Score: On-Time vs Late\nOn-Time avg: {on_time_scores.mean():.2f}  |  Late avg: {late_scores.mean():.2f}")
for score, label, color in [(on_time_scores.mean(),"",""), (late_scores.mean(),"","")]:
    pass
ax2.axhline(on_time_scores.mean(), xmin=0.05, xmax=0.45, color=GREEN, linestyle="--", alpha=0.7, linewidth=1.5)
ax2.axhline(late_scores.mean(),    xmin=0.55, xmax=0.95, color=RED,   linestyle="--", alpha=0.7, linewidth=1.5)

plt.tight_layout()
plt.savefig(f"{CHARTS}/04_delay_vs_review.png", bbox_inches="tight")
plt.close()
print(f"  ✓ Chart 4 saved  |  Correlation r = {correlation:.3f}")

# ════════════════════════════════════════════════════════════════════════════
# CHART 5 — Payment Methods & Installment Analysis
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 5: Payment Analysis...")

pay_dist = master["payment_type"].value_counts()
install  = master[master["payment_type"]=="credit_card"]["payment_installments"].value_counts().sort_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Payment Method Distribution & Credit Card Installments",
             fontsize=14, fontweight="bold")

wedge_colors = [BLUE, ORANGE, GREEN, PURPLE]
wedges, texts, autotexts = ax1.pie(
    pay_dist.values, labels=pay_dist.index,
    autopct="%1.1f%%", colors=wedge_colors,
    startangle=90, pctdistance=0.82,
    wedgeprops=dict(edgecolor="white", linewidth=2))
for at in autotexts:
    at.set_fontsize(10); at.set_fontweight("bold")
ax1.set_title("Payment Method Split")

ax2.bar(install.index.astype(str), install.values, color=BLUE, alpha=0.8, edgecolor="white")
ax2.set_xlabel("Number of Installments")
ax2.set_ylabel("Number of Orders")
ax2.set_title("Credit Card — Installment Distribution")

plt.tight_layout()
plt.savefig(f"{CHARTS}/05_payment_analysis.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 5 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 6 — Order Heatmap: Hour of Day × Day of Week
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 6: Order Timing Heatmap...")

master["hour"]    = pd.to_datetime(master["order_purchase_timestamp"]).dt.hour
master["weekday"] = pd.to_datetime(master["order_purchase_timestamp"]).dt.day_name()

day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
heatmap_data = master.groupby(["weekday","hour"])["order_id"].count().reset_index()
heatmap_pivot = heatmap_data.pivot(index="weekday", columns="hour", values="order_id").reindex(day_order)

fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(heatmap_pivot, cmap="Blues", ax=ax, linewidths=0.3,
            cbar_kws={"label":"Number of Orders"},
            annot=False)
ax.set_title("Order Volume Heatmap — Hour of Day × Day of Week",
             fontsize=14, fontweight="bold")
ax.set_xlabel("Hour of Day (0–23)")
ax.set_ylabel("")
plt.tight_layout()
plt.savefig(f"{CHARTS}/06_order_heatmap.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 6 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 7 — UNIQUE FEATURE: Seller Health Score Distribution
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 7: Seller Health Score (UNIQUE)...")

seller_stats = master.groupby("seller_id").agg(
    orders       = ("order_id",       "count"),
    revenue      = ("total_price",    "sum"),
    avg_score    = ("review_score",   "mean"),
    late_rate    = ("is_late",        "mean"),
    avg_delivery = ("delivery_days",  "mean"),
).reset_index()

# Seller Health Score = composite 0–100
# 40% review score (normalised), 40% on-time rate, 20% volume normalised
max_orders = seller_stats["orders"].max()
seller_stats["score_review"]   = (seller_stats["avg_score"] / 5) * 40
seller_stats["score_ontime"]   = (1 - seller_stats["late_rate"]) * 40
seller_stats["score_volume"]   = (seller_stats["orders"] / max_orders) * 20
seller_stats["health_score"]   = (seller_stats["score_review"] +
                                   seller_stats["score_ontime"] +
                                   seller_stats["score_volume"]).clip(0, 100)

# Tier labels
def tier(s):
    if s >= 75: return "Elite ⭐"
    elif s >= 55: return "Good ✅"
    elif s >= 35: return "Average ⚠️"
    else: return "At Risk 🔴"

seller_stats["tier"] = seller_stats["health_score"].apply(tier)
tier_counts = seller_stats["tier"].value_counts()
tier_order  = ["Elite ⭐","Good ✅","Average ⚠️","At Risk 🔴"]
tier_colors = [GREEN, BLUE, ORANGE, RED]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("🏆 Seller Health Score — Unique Composite KPI",
             fontsize=14, fontweight="bold")

ax1.hist(seller_stats["health_score"], bins=30, color=BLUE, edgecolor="white", alpha=0.85)
ax1.axvline(seller_stats["health_score"].mean(), color=RED, linestyle="--",
            label=f"Mean: {seller_stats['health_score'].mean():.1f}")
ax1.set_xlabel("Health Score (0–100)")
ax1.set_ylabel("Number of Sellers")
ax1.set_title("Distribution of Seller Health Scores")
ax1.legend()

bars_h = ax2.bar(
    [t for t in tier_order if t in tier_counts.index],
    [tier_counts.get(t,0) for t in tier_order if t in tier_counts.index],
    color=[c for t,c in zip(tier_order,tier_colors) if t in tier_counts.index],
    edgecolor="white"
)
for bar in bars_h:
    h = bar.get_height()
    ax2.text(bar.get_x()+bar.get_width()/2, h+5, f"{int(h)}", ha="center", fontsize=10, fontweight="bold")
ax2.set_ylabel("Number of Sellers")
ax2.set_title("Sellers by Performance Tier")

plt.tight_layout()
plt.savefig(f"{CHARTS}/07_seller_health_score.png", bbox_inches="tight")
plt.close()
seller_stats.to_csv(f"{PROC}/seller_health_scores.csv", index=False)
print(f"  ✓ Chart 7 saved  |  Tiers: {tier_counts.to_dict()}")

# ════════════════════════════════════════════════════════════════════════════
# CHART 8 — UNIQUE FEATURE: RFM Customer Segmentation
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 8: RFM Customer Segmentation (UNIQUE)...")

snapshot_date = pd.to_datetime(master["order_purchase_timestamp"]).max() + pd.Timedelta(days=1)
rfm = master.groupby("customer_id").agg(
    Recency   = ("order_purchase_timestamp", lambda x: (snapshot_date - pd.to_datetime(x).max()).days),
    Frequency = ("order_id",  "count"),
    Monetary  = ("total_price","sum"),
).reset_index()

# Score 1–4 (quartile-based)
rfm["R"] = pd.qcut(rfm["Recency"],   q=4, labels=[4,3,2,1]).astype(int)
rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=4, labels=[1,2,3,4]).astype(int)
rfm["M"] = pd.qcut(rfm["Monetary"],  q=4, labels=[1,2,3,4]).astype(int)
rfm["RFM_Score"] = rfm["R"] + rfm["F"] + rfm["M"]

def rfm_segment(row):
    if row["RFM_Score"] >= 10: return "Champions"
    elif row["RFM_Score"] >= 8: return "Loyal"
    elif row["R"] >= 3 and row["FM_avg"] >= 2: return "Potential Loyalists"
    elif row["R"] == 4 and row["FM_avg"] < 2: return "New Customers"
    elif row["R"] <= 2 and row["FM_avg"] >= 3: return "At Risk"
    else: return "Lost"

rfm["FM_avg"] = (rfm["F"] + rfm["M"]) / 2
rfm["Segment"] = rfm.apply(rfm_segment, axis=1)

seg_summary = rfm.groupby("Segment").agg(
    customers = ("customer_id","count"),
    avg_monetary = ("Monetary","mean"),
).reset_index().sort_values("customers", ascending=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("👥 RFM Customer Segmentation — Recency · Frequency · Monetary",
             fontsize=14, fontweight="bold")

seg_colors = {"Champions":GREEN,"Loyal":BLUE,"Potential Loyalists":"#06B6D4",
              "New Customers":ORANGE,"At Risk":RED,"Lost":"#6B7280"}
bar_colors = [seg_colors.get(s, BLUE) for s in seg_summary["Segment"]]

ax1.bar(seg_summary["Segment"], seg_summary["customers"],
        color=bar_colors, edgecolor="white")
ax1.set_xticklabels(seg_summary["Segment"], rotation=30, ha="right", fontsize=9)
ax1.set_ylabel("Number of Customers")
ax1.set_title("Customer Count by RFM Segment")
for bar, val in zip(ax1.patches, seg_summary["customers"]):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+20,
             f"{val:,}", ha="center", fontsize=9, fontweight="bold")

ax2.scatter(rfm["Recency"], rfm["Monetary"], c=[seg_colors.get(s,BLUE) for s in rfm["Segment"]],
            alpha=0.3, s=8)
ax2.set_xlabel("Recency (days since last order)")
ax2.set_ylabel("Total Spend (₹)")
ax2.set_title("RFM Scatter — Recency vs Monetary")
legend_p = [mpatches.Patch(color=c,label=s) for s,c in seg_colors.items()]
ax2.legend(handles=legend_p, fontsize=7.5, loc="upper right")

plt.tight_layout()
plt.savefig(f"{CHARTS}/08_rfm_segmentation.png", bbox_inches="tight")
plt.close()
rfm.to_csv(f"{PROC}/rfm_segments.csv", index=False)
print(f"  ✓ Chart 8 saved  |  Segments: {rfm['Segment'].value_counts().to_dict()}")

# ════════════════════════════════════════════════════════════════════════════
# CHART 9 — UNIQUE FEATURE: Revenue Forecast (Rolling Average)
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 9: Revenue Forecast...")

weekly = master.copy()
weekly["week"] = pd.to_datetime(weekly["order_purchase_timestamp"]).dt.to_period("W")
weekly_rev = weekly.groupby("week")["total_price"].sum().reset_index()
weekly_rev["week_dt"] = weekly_rev["week"].dt.to_timestamp()
weekly_rev["MA4"]  = weekly_rev["total_price"].rolling(4, min_periods=1).mean()
weekly_rev["MA8"]  = weekly_rev["total_price"].rolling(8, min_periods=1).mean()
last_ma8 = weekly_rev["MA8"].iloc[-1]
last_dt  = weekly_rev["week_dt"].iloc[-1]
future_dates = [last_dt + pd.Timedelta(weeks=i) for i in range(1,7)]
future_vals  = [last_ma8 * (1 + 0.01*i) for i in range(1,7)]

fig, ax = plt.subplots(figsize=(13, 5))
ax.plot(weekly_rev["week_dt"], weekly_rev["total_price"], color="#CBD5E1", linewidth=1, alpha=0.8, label="Actual Weekly")
ax.plot(weekly_rev["week_dt"], weekly_rev["MA4"], color=ORANGE, linewidth=2, label="4-Week MA")
ax.plot(weekly_rev["week_dt"], weekly_rev["MA8"], color=BLUE,   linewidth=2.5, label="8-Week MA (Trend)")
ax.plot(future_dates, future_vals, color=GREEN, linewidth=2, linestyle="--", label="6-Week Forecast")
ax.fill_between(future_dates,
                [v*0.88 for v in future_vals],
                [v*1.12 for v in future_vals],
                alpha=0.15, color=GREEN, label="Forecast ±12% band")
ax.axvline(last_dt, color=RED, linestyle=":", alpha=0.5)
ax.text(last_dt, ax.get_ylim()[1]*0.9, " Forecast →", color=RED, fontsize=9)
ax.set_title("Weekly Revenue with 8-Week Moving Average & 6-Week Forecast",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Week"); ax.set_ylabel("Revenue (₹)")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(f"{CHARTS}/09_revenue_forecast.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 9 saved")

# ════════════════════════════════════════════════════════════════════════════
# CHART 10 — Executive KPI Dashboard (Single Summary Chart)
# ════════════════════════════════════════════════════════════════════════════
print("Generating Chart 10: Executive KPI Dashboard...")

total_rev     = master["total_price"].sum()
total_orders  = len(master)
avg_order_val = master["total_price"].mean()
late_rate     = master["is_late"].mean() * 100
avg_review    = master["review_score"].mean()
avg_del_days  = master["delivery_days"].mean()

fig = plt.figure(figsize=(14, 9))
fig.patch.set_facecolor("#F8FAFC")
gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.5, wspace=0.4)

ax_title = fig.add_subplot(gs[0, :])
ax_title.axis("off")
ax_title.text(0.5, 0.7, "Retail Supply Chain Intelligence Dashboard",
              ha="center", va="center", fontsize=18, fontweight="bold", color="#0D3B6E")
ax_title.text(0.5, 0.15, "Olist E-Commerce  |  Jan 2017 – Nov 2018  |  96,000+ Orders Analysed",
              ha="center", va="center", fontsize=10, color="#64748B")

kpis = [
    ("Total Revenue",   f"₹{total_rev/1e6:.2f}M",  GREEN),
    ("Total Orders",    f"{total_orders:,}",         BLUE),
    ("Avg Order Value", f"₹{avg_order_val:.0f}",    PURPLE),
    ("Avg Review",      f"★ {avg_review:.2f}/5",    ORANGE),
    ("Late Rate",       f"{late_rate:.1f}%",         RED),
    ("Avg Delivery",    f"{avg_del_days:.1f} days",  "#0891B2"),
    ("Active Sellers",  f"{master['seller_id'].nunique():,}", "#CA8A04"),
    ("States Covered",  f"{master['customer_state'].nunique()}",  "#7C3AED"),
]
positions = [(1,0),(1,1),(1,2),(1,3),(2,0),(2,1),(2,2),(2,3)]
for (r,c),(label, value, color) in zip(positions, kpis):
    ax = fig.add_subplot(gs[r, c])
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_edgecolor(color); spine.set_linewidth(2)
    ax.text(0.5, 0.65, value,  ha="center", va="center", fontsize=16,
            fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.2,  label, ha="center", va="center", fontsize=8.5,
            color="#64748B",  transform=ax.transAxes)
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)

plt.savefig(f"{CHARTS}/10_executive_dashboard.png", bbox_inches="tight", dpi=140)
plt.close()
print("  ✓ Chart 10 saved")

print("\n" + "="*60)
print("✅ All 10 charts generated in outputs/charts/")
print("="*60)
for f in sorted(os.listdir(CHARTS)):
    print(f"  {f}")
