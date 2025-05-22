import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

df = pd.read_sql(
    "SELECT * FROM monthly_metrics ORDER BY month",
    engine,
    parse_dates=["month"]
)
print(df.to_string(index=False))
