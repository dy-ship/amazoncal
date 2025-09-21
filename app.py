# app_wechat_ready.py
# If you prefer to replace your current app.py, rename this file to app.py
# and keep the verify TXT file in the same folder.

import streamlit as st
from pathlib import Path

# ---- WeChat verify route ----
VERIFY_FILE = "552bb7948e5cd9764c7b67dfc64d53c4.txt"

def _mount_wechat_verify():
    try:
        from streamlit.web.server.server import Server
        from starlette.responses import FileResponse, PlainTextResponse

        server = Server.get_current()
        if server is None or not hasattr(server, "_app"):
            return

        app = server._app
        vf = Path(VERIFY_FILE).resolve()

        @app.get(f"/{VERIFY_FILE}")
        def wechat_verify():
            if vf.exists():
                return FileResponse(str(vf), media_type="text/plain; charset=utf-8")
            return PlainTextResponse("verify file not found", status_code=404)

    except Exception as e:
        print("[wechat-verify] mount failed:", e)

_mount_wechat_verify()
# ---- end verify route ----

# ---- Minimal UI (keep your original UI if you already have one) ----
st.set_page_config(page_title="Amazon Profit Calculator", page_icon="🧮", layout="centered")
st.title("Amazon Profit Calculator")
st.caption("This is a minimal placeholder UI. Replace with your existing calculator if needed.")

col1, col2 = st.columns(2)
with col1:
    price = st.number_input("售价 (USD)", min_value=0.0, value=59.99, step=0.01)
    shipping = st.number_input("头程运费", min_value=0.0, value=5.0, step=0.01)
    fba = st.number_input("FBA 配送费", min_value=0.0, value=6.5, step=0.01)
with col2:
    commission_rate = st.number_input("佣金率 %", min_value=0.0, max_value=30.0, value=15.0, step=0.1)
    ad_rate = st.number_input("广告费率 %", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
    return_rate = st.number_input("退货率 %", min_value=0.0, max_value=100.0, value=5.0, step=0.1)

commission = price * commission_rate/100
ads = price * ad_rate/100
returns_cost = price * return_rate/100

gross_profit = price - shipping - fba - commission
net_profit = price - shipping - fba - commission - ads - returns_cost

st.subheader("结果")
st.write(f"毛利润：**${gross_profit:.2f}**")
st.write(f"净利润：**${net_profit:.2f}**")
if price > 0:
    st.write(f"净利率：**{(net_profit/price*100):.2f}%**")

st.info("如需保留你原来的应用逻辑，只需在你现有的 app.py 顶部加一行：`import wechat_patch`。")
