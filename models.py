# models.py
from sqlalchemy import Column, Date, Integer, Numeric, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    charge_id   = Column(String, primary_key=True)
    customer_id = Column(String, index=True)
    amount_jpy  = Column(Numeric)      # JPY 換算済み金額
    paid_at     = Column(Date)         # 支払日（UTC）

class MonthlyMetric(Base):
    __tablename__ = "monthly_metrics"
    month         = Column(Date, primary_key=True)  # 月初日で識別
    new_cnt       = Column(Integer)
    repeat_cnt    = Column(Integer)
    resurrect_cnt = Column(Integer)
    churn_cnt     = Column(Integer)
    active_cnt    = Column(Integer)
    arpu          = Column(Numeric)
    churn_rate    = Column(Numeric)
    ltv           = Column(Numeric)
