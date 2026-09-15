# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import auth
import data_manager as dm

st.set_page_config(page_title="ثبت محصولات", page_icon="📦", layout="wide")
auth.require_permission("products")


st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        📦 ثبت محصولات
    </h1>
    """,
    unsafe_allow_html=True
)

if auth.can_write("products"):
    with st.expander("➕ افزودن محصول جدید", expanded=True):
        with st.form("add_product_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                code = st.text_input("کد محصول *")
                name = st.text_input("نام محصول *")
                unit = st.text_input("واحد", value="عدد")
            with c2:
                opening_stock = st.number_input(
                    "موجودی اولیه",
                    min_value=0.0, value=0.0, step=1.0
                )
                min_stock = st.number_input(
                    "حداقل موجودی مجاز (هشدار کمبود)",
                    min_value=0.0, value=0.0, step=1.0
                )
                daily_capacity = st.number_input(
                    "ظرفیت تولید روزانه",
                    min_value=0.0, value=0.0, step=1.0,
                    help="۰ یعنی محدودیت ظرفیت ثبت نشده و سیستم کل نیاز را در بازه برنامه‌ریزی قرار می‌دهد."
                )

            submitted = st.form_submit_button("افزودن محصول")
            if submitted:
                if not code or not name:
                    st.error("کد محصول و نام محصول الزامی است.")
                else:
                    ok, msg = dm.add_product(
                        code.strip(), name.strip(), unit.strip(),
                        opening_stock, min_stock, daily_capacity
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
else:
    st.info("شما فقط دسترسی مشاهده این بخش را دارید.")

st.subheader("لیست محصولات")
products = dm.get_products()
if products.empty:
    st.info("هنوز هیچ محصولی ثبت نشده است.")
else:
    view = products.copy()
    view["OpeningStock"] = pd.to_numeric(view["OpeningStock"], errors="coerce").fillna(0)
    view["DailyProductionCapacity"] = pd.to_numeric(view.get("DailyProductionCapacity", 0), errors="coerce").fillna(0)
    view = view.rename(columns={
        "OpeningStock": "موجودی اولیه",
        "DailyProductionCapacity": "ظرفیت تولید روزانه"
    })
    st.dataframe(view, use_container_width=True, hide_index=True)
