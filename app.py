# app.py — Amazon Profit Calculator (Full UI) + WeChat Verify Route
# Author: dyu + ChatGPT
# Desc : Full calculator with manual inputs (price, logistics, FBA, commission, ads, returns),
#        discount scenarios, export to Excel, and a WeChat verification route for Streamlit on Zeabur.

import math
from pathlib import Path
from io import BytesIO
import pandas as pd
import streamlit as st

# ========== WeChat verify route (for Streamlit internal FastAPI) ==========
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
# ========================= End verify route ===============================


# -------------------------- Helper Functions ------------------------------
def calc_profit(price, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost=0.0):
    """
    Return a dict with gross/net profit & margins.
    price: 售价
    first_leg: 头程
    fba_fee: FBA 配送费
    commission_rate: 亚马逊佣金率 (0-100)
    ad_rate: 广告费率 (0-100)
    return_rate: 退货率 (0-100), 假设退货时佣金不退还且由卖家承担运费（可在extra_cost体现）
    extra_cost: 其他成本（包装、配件、售后等，可选）
    """
    commission = price * commission_rate / 100.0
    ad_cost   = price * ad_rate / 100.0
    return_cost = price * return_rate / 100.0   # 简化：把退货损失近似看作按售价的百分比
    gross_profit = price - first_leg - fba_fee - commission - extra_cost
    net_profit   = price - first_leg - fba_fee - commission - ad_cost - return_cost - extra_cost
    gross_margin = (gross_profit / price * 100.0) if price > 0 else 0.0
    net_margin   = (net_profit   / price * 100.0) if price > 0 else 0.0
    return {
        "commission": commission,
        "ad_cost": ad_cost,
        "return_cost": return_cost,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "gross_margin": gross_margin,
        "net_margin": net_margin
    }


def as_money(x):
    return f"${x:,.2f}"


def export_to_excel(rows):
    """
    rows: list of dicts with calculation results to a single Excel (one sheet).
    """
    df = pd.DataFrame(rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Profit")
        ws = writer.sheets["Profit"]
        # Optional: format widths
        for i, col in enumerate(df.columns):
            width = max(12, min(40, int(df[col].astype(str).map(len).max()) + 2))
            ws.set_column(i, i, width)
    output.seek(0)
    return output, df


# --------------------------------- UI -------------------------------------
st.set_page_config(page_title="Amazon Profit Calculator", page_icon="📦", layout="wide")

st.title("📦 Amazon Profit Calculator")
st.caption("售价、头程、FBA、佣金、广告费、退货率都可手动输入；支持折扣场景与导出 Excel。")

with st.expander("基础设置 / Basic Settings", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.number_input("售价 (USD)", min_value=0.0, value=59.99, step=0.01)
        first_leg = st.number_input("头程运费 / First leg", min_value=0.0, value=5.0, step=0.01)
    with c2:
        fba_fee = st.number_input("FBA 配送费 / FBA fee", min_value=0.0, value=6.50, step=0.01)
        extra_cost = st.number_input("其他成本 / Extra cost", min_value=0.0, value=0.00, step=0.01, help="包装、配件、售后等其他成本")
    with c3:
        commission_rate = st.number_input("佣金率 % / Commission", min_value=0.0, max_value=30.0, value=15.0, step=0.1)
        ad_rate = st.number_input("广告费率 % / Ads", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
        return_rate = st.number_input("退货率 % / Returns", min_value=0.0, max_value=100.0, value=5.0, step=0.1,
                                      help="简化处理：退货的损失按售价的百分比计入")

st.divider()

# 主场景（原价）
base = calc_profit(price, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)

# 折扣场景设置
st.subheader("折扣场景 / Discount Scenarios")
d1, d2, d3 = st.columns(3)
with d1:
    enable_80 = st.checkbox("启用 8 折 (20% off)", value=True)
with d2:
    enable_50 = st.checkbox("启用 5 折 (50% off)", value=False)
with d3:
    custom_disc = st.slider("自定义折扣 %（0=无折扣）", 0, 90, 0, step=5)
    enable_custom = custom_disc > 0

rows = []
def append_row(label, p):
    rows.append({
        "场景": label,
        "售价": round(p, 2),
        "头程": round(first_leg, 2),
        "FBA": round(fba_fee, 2),
        "佣金率%": round(commission_rate, 2),
        "广告率%": round(ad_rate, 2),
        "退货率%": round(return_rate, 2),
        "其他成本": round(extra_cost, 2),
        "佣金": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["commission"], 2),
        "广告费": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["ad_cost"], 2),
        "退货损失": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["return_cost"], 2),
        "毛利润": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["gross_profit"], 2),
        "毛利率%": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["gross_margin"], 2),
        "净利润": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["net_profit"], 2),
        "净利率%": round(calc_profit(p, first_leg, fba_fee, commission_rate, ad_rate, return_rate, extra_cost)["net_margin"], 2),
    })

# 原价
append_row("原价", price)
# 8 折
if enable_80:
    append_row("8折", price * 0.8)
# 5 折
if enable_50:
    append_row("5折", price * 0.5)
# 自定义
if enable_custom:
    rate = max(0, min(90, custom_disc))
    append_row(f"{100-rate}折", price * (1 - rate/100.0))

df = pd.DataFrame(rows)

# 展示结果卡片
st.subheader("当前售价结果 / Current Price")
k1, k2, k3, k4 = st.columns(4)
k1.metric("毛利润", as_money(base["gross_profit"]))
k2.metric("毛利率", f'{base["gross_margin"]:.2f}%')
k3.metric("净利润", as_money(base["net_profit"]))
k4.metric("净利率", f'{base["net_margin"]:.2f}%')

with st.expander("详细明细 / Breakdown (当前售价)", expanded=False):
    st.write({
        "佣金": as_money(base["commission"]),
        "广告费": as_money(base["ad_cost"]),
        "退货损失": as_money(base["return_cost"]),
        "头程": as_money(first_leg),
        "FBA": as_money(fba_fee),
        "其他成本": as_money(extra_cost),
    })

st.subheader("场景对比 / Scenarios")
st.dataframe(df, use_container_width=True)

# 导出
col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    excel_bytes, excel_df = export_to_excel(rows)
    st.download_button(
        label="下载 Excel 报表",
        data=excel_bytes,
        file_name="amazon_profit_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with col_dl2:
    st.download_button(
        label="下载 CSV 报表",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="amazon_profit_report.csv",
        mime="text/csv"
    )

st.caption("提示：若微信里仍有风险提示，可在页面右上角选择“在浏览器中打开”。本应用已支持微信站长认证文件路由。")
