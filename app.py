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
        return f"✅ ログイン成功: UID={uid}"
    except Exception as e:
        return f"❌ ログイン失敗: {e}"

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
    # ltv列の None を NaN に置き換えて float 型に
    df["ltv"] = pd.to_numeric(df["ltv"], errors="coerce")
    return df

# ----------------------------------------
# Gradio UI
# ----------------------------------------
with gr.Blocks(title="LTV Dashboard") as demo:
    gr.Markdown("# 📊 LTV ダッシュボード")

    # Firebase JS SDK(Compat) 読み込み
    gr.HTML("""
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
    """)

    # 隠しトークンボックス（JS がここにセット）
    token_box = gr.Textbox(visible=False)

    # ログインボタン＆ステータス表示
    login_btn    = gr.Button("Google でログイン")
    login_status = gr.Markdown("🔒 未ログイン")

    # ① JS でトークン取得 → token_box にセット
    login_btn.click(
        fn=None,
        inputs=[],
        outputs=[token_box],
        js=f"""
async () => {{
  const config = {{
    apiKey: "{os.getenv('FIREBASE_API_KEY')}",
    authDomain: "{os.getenv('FIREBASE_PROJECT_ID')}.firebaseapp.com",
    projectId: "{os.getenv('FIREBASE_PROJECT_ID')}"
  }};
  firebase.initializeApp(config);
  const provider = new firebase.auth.GoogleAuthProvider();
  const result   = await firebase.auth().signInWithPopup(provider);
  const token    = await result.user.getIdToken();
  document.querySelector("textarea").value = token;
}}
"""
    )
    # ② Python でトークン検証 → ステータス更新
    login_btn.click(verify_token, token_box, login_status)

    # 認証後に表示するタブ
    with gr.Tabs():
        with gr.TabItem("月次トレンド"):
            df = load_metrics_df()
            # wide-form を避け、long-form に変換
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
