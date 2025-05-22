#!/usr/bin/env python
import os
import datetime
import stripe
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Payment
from dotenv import load_dotenv
import pandas as pd

# ----------------------------------------
# 設定読み込み
# ----------------------------------------
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")

# ----------------------------------------
# DB 接続＆セッション準備
# ----------------------------------------
engine = create_engine(os.getenv("DATABASE_URL"))
Session = sessionmaker(bind=engine)

# ----------------------------------------
# テーブル定義反映
# ----------------------------------------
def init_db():
    Base.metadata.create_all(engine)

# ----------------------------------------
# Stripe から支払いデータを取得し保存（テスト用 5 件）
# ----------------------------------------
def sync_payments(limit=5):
    print(f"⏳ Fetching latest {limit} charges (test mode)…")
    resp = stripe.Charge.list(limit=limit)
    sess = Session()
    # テスト用に既存データをクリア
    sess.execute(text("TRUNCATE TABLE payments"))
    objs = []
    for ch in resp.data:
        paid_at = datetime.date.fromtimestamp(ch.created)
        amt_jpy = Decimal(ch.amount) / Decimal(100)
        objs.append(
            Payment(
                charge_id   = ch.id,
                customer_id = ch.customer,
                amount_jpy  = amt_jpy,
                paid_at     = paid_at
            )
        )
    # bulk で一括INSERT
    sess.bulk_save_objects(objs)
    sess.commit()
    sess.close()
    print(f"✅ Synced {len(objs)} payments.")

# ----------------------------------------
# 月次指標を再計算して保存
# ----------------------------------------
def calc_metrics():
    print("🔧 Calculating monthly metrics…")
    # payments テーブルを DataFrame で読み込み
    df = pd.read_sql(
        "SELECT customer_id, amount_jpy, paid_at FROM payments",
        engine,
        parse_dates=["paid_at"]
    )
    if df.empty:
        print("⚠️  No payments to process.")
        return

    # 月キー作成
    df["month"] = df["paid_at"].dt.to_period("M").dt.to_timestamp()

    # 顧客×月 の売上合計
    grp = df.groupby(["month", "customer_id"])["amount_jpy"].sum().reset_index()

    metrics = []
    seen = set()
    prev_month = set()

    for month in sorted(grp["month"].unique()):
        dfm = grp[grp["month"] == month]
        customers = set(dfm["customer_id"])
        total_rev = dfm["amount_jpy"].sum()
        active_cnt = len(customers)

        new_cust      = customers - seen
        repeat_cust   = customers & prev_month
        resurrect_cust= {c for c in customers if c in seen and c not in prev_month}
        churn_cust    = prev_month - customers

        new_cnt       = len(new_cust)
        repeat_cnt    = len(repeat_cust)
        resurrect_cnt = len(resurrect_cust)
        churn_cnt     = len(churn_cust)
        arpu          = total_rev / active_cnt if active_cnt else 0
        churn_rate    = churn_cnt / active_cnt if active_cnt else 0
        ltv           = arpu / churn_rate if churn_rate else None

        metrics.append({
            "month": month,
            "new_cnt": new_cnt,
            "repeat_cnt": repeat_cnt,
            "resurrect_cnt": resurrect_cnt,
            "churn_cnt": churn_cnt,
            "active_cnt": active_cnt,
            "arpu": arpu,
            "churn_rate": churn_rate,
            "ltv": ltv
        })

        seen |= customers
        prev_month = customers

    # monthly_metrics テーブルを置き換え
    dfm = pd.DataFrame(metrics)
    dfm.to_sql("monthly_metrics", engine, if_exists="replace", index=False)
    print("✅ monthly_metrics updated")

# ----------------------------------------
# スクリプト実行
# ----------------------------------------
if __name__ == "__main__":
    init_db()
    sync_payments(limit=5)   # テスト：最新5件だけ持ってくる
    calc_metrics()
    print("🎉 Test ETL complete")
