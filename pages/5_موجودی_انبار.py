# -*- coding: utf-8 -*-
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="موجودی انبار", page_icon="📊", layout="wide")
auth.require_permission("inventory")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        📊 موجودی فعلی انبار
    </h1>
    """,
    unsafe_allow_html=True
)
inventory = dm.compute_inventory()

if inventory.empty:
    st.info("هنوز محصولی ثبت نشده است.")
    st.stop()

search = st.text_input("جستجو در نام یا کد محصول")
view = inventory.copy()
if search:
    mask = (
        view["ProductName"].astype(str).str.contains(search, case=False, na=False)
        | view["ProductCode"].astype(str).str.contains(search, case=False, na=False)
    )
    view = view[mask]

st.dataframe(view, use_container_width=True, hide_index=True)

st.divider()
csv = view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ دانلود جدول CSV", data=csv,
    file_name="موجودی_انبار.csv", mime="text/csv"
)
