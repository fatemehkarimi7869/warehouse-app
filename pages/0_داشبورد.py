# -*- coding: utf-8 -*-
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="داشبورد", page_icon="🏠", layout="wide")
auth.require_permission("dashboard")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        🏠 داشبورد سامانه مدیریت تولید و انبار رامون
    </h1>
    """,
    unsafe_allow_html=True
)


inventory = dm.compute_inventory()
plan = dm.compute_production_plan()

col1, col2, col3, col4 = st.columns(4)
col1.metric("تعداد محصولات", len(dm.get_products()))

if not inventory.empty:
    low_stock = inventory[inventory["موجودی فعلی"] < inventory["MinStock"]]
else:
    low_stock = inventory

col2.metric("محصولات زیر حد مجاز", len(low_stock))

if not plan.empty and "تولید موردنیاز روز" in plan.columns:
    need_produce = plan[plan["تولید موردنیاز روز"] > 0]
else:
    need_produce = plan

col3.metric("روزهای نیازمند تولید", len(need_produce))
col4.metric(
    "جمع موجودی کل",
    int(inventory["موجودی فعلی"].sum()) if not inventory.empty else 0
)

st.divider()

if not low_stock.empty:
    st.warning("⚠️ محصولات زیر حد مجاز موجودی:")
    st.dataframe(low_stock, use_container_width=True, hide_index=True)

if not need_produce.empty:
    st.info("📋 برنامه تولید روزانه:")
    st.dataframe(
        need_produce,
        use_container_width=True, hide_index=True
    )

st.subheader("📦 موجودی فعلی انبار")
if inventory.empty:
    st.info("هنوز محصولی ثبت نشده است.")
else:
    st.dataframe(inventory, use_container_width=True, hide_index=True)

st.divider()
st.subheader("⬇️ خروجی اکسل کامل")
excel_bytes = dm.export_to_excel_bytes()
st.download_button(
    "دانلود گزارش کامل اکسل",
    data=excel_bytes,
    file_name="گزارش_انبار.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
