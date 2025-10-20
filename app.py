# app.py — Amazon Profit Calculator (Full UI) + WeChat Verify Route
# Author: dyu + ChatGPT
# Desc : Full calculator with manual inputs (price, logistics, FBA, commission, ads, returns),
#        discount scenarios, export to Excel (WITH FORMULAS), and a WeChat verification route for Streamlit on Zeabur.

import math
from pathlib import Path
from io import BytesIO
import pandas as pd
import streamlit as st
import threading, time

# ========== WeChat verify route (for Streamlit internal FastAPI) ==========
VERIFY_FILE = "552bb7948e5cd9764c7b67dfc64d53c4.txt"
def _try_mount():
    from streamlit.web.server.server import Server
    from starlette.responses import FileResponse, PlainTextResponse

    server = Server.get_current()
    if server is None or not hasattr(server, "_app"):
        return False  # server not ready yet

    app = server._app
    vf = Path(VERIFY_FILE).resolve()

    # 避免重复注册路由
    route_path = "/" + VERIFY_FILE
    for r in getattr(app.router, "routes", []):
        if getattr(r, "path", None) == route_path:
            return True

    @app.get(route_path)
    def wechat_verify():
        if vf.exists():
            return FileResponse(str(vf), media_type="text/plain; charset=utf-8")
        return PlainTextResponse("verify file not found", status_code=404)

    print("[wechat-verify] mounted:", route_path)
    return True

def _mount_wechat_verify_async():
    def worker():
        for _ in range(20):  # 最多尝试 20 次
            try:
                if _try_mount():
                    return
            except Exception as e:
                print("[wechat-verify] error:", e)
            time.sleep(0.5)
        print("[wechat-verify] failed to mount within timeout")

    threading.Thread(target=worker, daemon=True).start()

_mount_wechat_verify_async()
   
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
    导出带公式的 Excel：
    A 列 场景（文本）
    B 列 售价
    C 列 头程
    D 列 FBA
    E 列 佣金率%
    F 列 广告率%
    G 列 退货率%
    H 列 其他成本
    I 列 佣金 = B*E/100
    J 列 广告费 = B*F/100
    K 列 退货损失 = B*G/100
    L 列 毛利润 = B - C - D - I - H
    M 列 毛利率% = L/B*100
    N 列 净利润 = B - C - D - I - J - K - H
    O 列 净利率% = N/B*100
    """
    output = BytesIO()
    headers = [
        "场景","售价","头程","FBA","佣金率%","广告率%","退货率%","其他成本",
        "佣金","广告费","退货损失","毛利润","毛利率%","净利润","净利率%"
    ]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # 先写一个空表头（后续逐格写入值与公式）
        pd.DataFrame(columns=headers).to_excel(writer, index=False, sheet_name="Profit")
        ws = writer.sheets["Profit"]

        start_row = 1  # 数据从第2行开始（第1行为表头）

        # 写入 A–H 列的原始值
        for i, r in enumerate(rows):
            row_idx = start_row + i  # 0-based
            # A 列 文本：场景
            ws.write_string(row_idx, 0, str(r.get("场景", "")))
            # B–H 数值
            ws.write_number(row_idx, 1, float(r.get("售价", 0)))
            ws.write_number(row_idx, 2, float(r.get("头程", 0)))
            ws.write_number(row_idx, 3, float(r.get("FBA", 0)))
            ws.write_number(row_idx, 4, float(r.get("佣金率%", 0)))
            ws.write_number(row_idx, 5, float(r.get("广告率%", 0)))
            ws.write_number(row_idx, 6, float(r.get("退货率%", 0)))
            ws.write_number(row_idx, 7, float(r.get("其他成本", 0)))

        # 为 I–O 列写入公式
        n = len(rows)
        for i in range(n):
            row_idx = start_row + i      # 0-based
            xrow = row_idx + 1           # Excel 1-based 行号
            # 佣金、广告费、退货损失
            ws.write_formula(row_idx, 8,  f"=B{xrow}*E{xrow}/100")
            ws.write_formula(row_idx, 9,  f"=B{xrow}*F{xrow}/100")
            ws.write_formula(row_idx, 10, f"=B{xrow}*G{xrow}/100")
            # 毛利润、毛利率
            ws.write_formula(row_idx, 11, f"=B{xrow}-C{xrow}-D{xrow}-I{xrow}-H{xrow}")
            ws.write_formula(row_idx, 12, f"=IF(B{xrow}>0,L{xrow}/B{xrow}*100,0)")
            # 净利润、净利率
            ws.write_formula(row_idx, 13, f"=B{xrow}-C{xrow}-D{xrow}-I{xrow}-J{xrow}-K{xrow}-H{xrow}")
            ws.write_formula(row_idx, 14, f"=IF(B{xrow}>0,N{xrow}/B{xrow}*100,0)")

        # 适当调宽列宽
        widths = [10,10,10,10,10,10,10,10,10,10,10,12,10,12,10]
        for col, w in enumerate(widths):
            ws.set_column(col, col, w)

    output.seek(0)
    # 为兼容原有调用返回 DataFrame（展示可继续用 df = pd.DataFrame(rows)）
    return output, pd.DataFrame(rows)


# --------------------------------- UI -------------------------------------
st.set_page_config(page_title="Amazon Profit Calculator", page_icon="📦", layout="wide")

st.title("📦 Amazon Profit Calculator")
st.caption("售价、头程、FBA、佣金、广告费、退货率都可手动输入；支持折扣场景与导出 Excel（含公式）。")

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
        # 下列字段在导出 Excel 时用公式计算，这里保留 DataFrame 显示需要
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

# 用于前端展示
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
