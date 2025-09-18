
import streamlit as st
import pandas as pd
import datetime as dt
from io import BytesIO

st.set_page_config(page_title="亚马逊利润计算器", page_icon="📦", layout="centered")

st.title("📦 亚马逊利润计算器（Zeabur / Streamlit）")

with st.expander("使用说明", expanded=True):
    st.markdown(
        "- 输入售价、折扣、退货率、广告费率、佣金费率、成本、头程、FBA，以及数量；\n"
        "- 计算出：毛利润/毛利率、净利润/净利率；\n"
        "- 点击下方按钮可导出到 Excel（不会写入服务器磁盘，直接浏览器下载）。"
    )

def calc(price, discount_rate, return_rate, ad_rate, commission_rate, cost, first_leg, fba_fee, qty):
    price_after_discount = price * (1 - discount_rate)
    revenue_per_unit = price_after_discount * (1 - return_rate)
    commission_per_unit = price_after_discount * commission_rate
    ad_cost_per_unit = price_after_discount * ad_rate
    variable_costs_ex_ad_per_unit = cost + first_leg + fba_fee + commission_per_unit

    gross_profit_per_unit = revenue_per_unit - variable_costs_ex_ad_per_unit
    gross_margin = (gross_profit_per_unit / revenue_per_unit) if revenue_per_unit != 0 else 0.0
    net_profit_per_unit = gross_profit_per_unit - ad_cost_per_unit
    net_margin = (net_profit_per_unit / revenue_per_unit) if revenue_per_unit != 0 else 0.0

    revenue = revenue_per_unit * qty
    gross_profit = gross_profit_per_unit * qty
    net_profit = net_profit_per_unit * qty
    ad_cost_total = ad_cost_per_unit * qty
    commission_total = commission_per_unit * qty
    total_cost_ex_ad = (cost + first_leg + fba_fee) * qty

    return {
        "折后单价": price_after_discount,
        "单件有效收入": revenue_per_unit,
        "总收入": revenue,
        "单件佣金": commission_per_unit,
        "总佣金": commission_total,
        "单件广告费": ad_cost_per_unit,
        "总广告费": ad_cost_total,
        "(不含广)合计成本": total_cost_ex_ad,
        "单件毛利润": gross_profit_per_unit,
        "总毛利润": gross_profit,
        "毛利率(%)": gross_margin * 100,
        "单件净利润": net_profit_per_unit,
        "总净利润": net_profit,
        "净利率(%)": net_margin * 100,
    }

with st.form("inputs"):
    col1, col2 = st.columns(2)
    with col1:
        price = st.number_input("售价", min_value=0.0, step=0.01, value=59.99)
        discount_rate = st.number_input("产品折扣(%)", min_value=0.0, max_value=100.0, step=0.1, value=0.0) / 100.0
        return_rate = st.number_input("退货率(%)", min_value=0.0, max_value=100.0, step=0.1, value=5.0) / 100.0
        ad_rate = st.number_input("广告费率(%)", min_value=0.0, max_value=100.0, step=0.1, value=15.0) / 100.0
    with col2:
        commission_rate = st.number_input("亚马逊佣金费率(%)", min_value=0.0, max_value=100.0, step=0.1, value=15.0) / 100.0
        cost = st.number_input("产品成本", min_value=0.0, step=0.01, value=20.0)
        first_leg = st.number_input("头程运费/件", min_value=0.0, step=0.01, value=3.2)
        fba_fee = st.number_input("FBA配送费/件", min_value=0.0, step=0.01, value=6.5)
    qty = st.number_input("数量", min_value=1, step=1, value=1)
    submitted = st.form_submit_button("计算")

if submitted:
    res = calc(price, discount_rate, return_rate, ad_rate, commission_rate, cost, first_leg, fba_fee, qty)
    colA, colB = st.columns(2)
    with colA:
        st.metric("毛利润 (总)", f"{res['总毛利润']:.2f}")
        st.metric("毛利率", f"{res['毛利率(%)']:.2f}%")
    with colB:
        st.metric("净利润 (总)", f"{res['总净利润']:.2f}")
        st.metric("净利率", f"{res['净利率(%)']:.2f}%")

    # 明细表
    df = pd.DataFrame([{
        "时间": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "售价": price,
        "产品折扣(%)": discount_rate * 100,
        "退货率(%)": return_rate * 100,
        "广告费率(%)": ad_rate * 100,
        "佣金费率(%)": commission_rate * 100,
        "成本": cost, "头程": first_leg, "FBA": fba_fee, "数量": qty,
        **res
    }])
    st.dataframe(df, use_container_width=True)

    # 导出到 Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="结果")
    st.download_button(
        "导出 Excel",
        data=output.getvalue(),
        file_name=f"amazon_profit_results_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.caption("假设：退货仅影响收入；佣金/成本/头程/FBA/广告费按下单计提。")
