import os
import gradio as gr
import firebase_admin
from firebase_admin import auth, credentials
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# ----------------------------------------
# 設定読み込み＆初期化
# ----------------------------------------
load_dotenv()
cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred, {
    "projectId": os.getenv("FIREBASE_PROJECT_ID")
})
engine = create_engine(os.getenv("DATABASE_URL"))

# ----------------------------------------
# 認証検証関数
# ----------------------------------------
def verify_token(id_token: str):
    try:
        uid = auth.verify_id_token(id_token)["uid"]
        return True, f"✅ ログイン成功: UID={uid}"
    except Exception as e:
        return False, f"❌ ログイン失敗: {e}"

# ----------------------------------------
# 月次KPI読み込み関数
# ----------------------------------------
def load_metrics_df():
    df = pd.read_sql(
        "SELECT month, new_cnt, repeat_cnt, resurrect_cnt, churn_cnt, active_cnt, arpu, churn_rate, ltv "
        "FROM monthly_metrics ORDER BY month",
        engine,
        parse_dates=["month"]
    )
    df["ltv"] = pd.to_numeric(df["ltv"], errors="coerce")
    return df

# ----------------------------------------
# カスタムCSSテーマ
# ----------------------------------------
custom_css = """
:root {
  --brand-primary: #2E3B4E;
  --brand-secondary: #F0A500;
  --bg: #FFFFFF;
  --fg: #333333;
  --card-bg: #F9F9F9;
  --border-radius: 8px;
}
#title { font-family: 'Segoe UI', sans-serif; color: var(--brand-primary); text-align: center; }
.token-col { background-color: var(--card-bg); padding: 16px; border-radius: var(--border-radius); }
.metrics-col { background-color: var(--bg); padding: 16px; }
button { background-color: var(--brand-secondary); color: white !important; border: none; padding: 8px 16px; border-radius: var(--border-radius); cursor: pointer; }
button:hover { opacity: 0.9; }
"""

# ----------------------------------------
# Gradio UI
# ----------------------------------------
with gr.Blocks(css=custom_css, title="LTV Dashboard") as demo:
    gr.Markdown("# 📊 LTV ダッシュボード", elem_id="title")

    # Firebase JS SDK(Compat)を読み込む
    gr.HTML("""
<script src=\"https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js\"></script>
<script src=\"https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js\"></script>
    """)

    with gr.Row():
        # 左カラム：ログイン／ステータス
        with gr.Column(scale=1, elem_classes=["token-col"]):
            token_box = gr.Textbox(visible=False)
            login_btn = gr.Button("Googleでログイン")
            login_status = gr.Markdown("🔒 未ログイン")

            # JSでトークン取得→Python検証
            login_btn.click(
                fn=None, inputs=[], outputs=[token_box],
                js=f"""
async () => {{
  const config = {{
    apiKey: \"{os.getenv('FIREBASE_API_KEY')}\",
    authDomain: \"{os.getenv('FIREBASE_PROJECT_ID')}.firebaseapp.com\",
    projectId: \"{os.getenv('FIREBASE_PROJECT_ID')}\"
  }};
  firebase.initializeApp(config);
  const provider = new firebase.auth.GoogleAuthProvider();
  const result = await firebase.auth().signInWithPopup(provider);
  const token = await result.user.getIdToken();
  document.querySelector('textarea').value = token;
}}"""
            )
            login_btn.click(verify_token, token_box, login_status)

        # 右カラム：KPI
        with gr.Column(scale=3, elem_classes=["metrics-col"]):
            with gr.Tabs():
                with gr.TabItem("月次トレンド"):
                    df = load_metrics_df()
                    long_df = df.melt(
                        id_vars="month",
                        value_vars=["new_cnt", "repeat_cnt", "churn_rate", "ltv"],
                        var_name="指標",
                        value_name="値"
                    )
                    fig = px.line(
                        long_df,
                        x="month",
                        y="値",
                        color="指標",
                        labels={"値": "人数/率", "month": "月"},
                        title="月次KPI推移"
                    )
                    gr.Plot(fig)

                with gr.TabItem("データ表"):
                    df2 = load_metrics_df()
                    gr.Dataframe(df2, label="月次KPIデータ", interactive=False)

if __name__ == "__main__":
    demo.launch()
