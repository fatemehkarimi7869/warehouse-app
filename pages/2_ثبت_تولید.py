# -*- coding: utf-8 -*-
import streamlit as st
import jdatetime
from streamlit_nej_datepicker import datepicker_component, Config
import auth
import data_manager as dm

st.set_page_config(page_title="ثبت تولید", page_icon="🏭", layout="wide")
auth.require_permission("production")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        🏭 ثبت تولید محصول
    </h1>
    """,
    unsafe_allow_html=True
)

products = dm.get_products()

if products.empty:
    st.warning("ابتدا محصول تعریف کنید.")
    st.stop()

product_options = {
    f"{row.ProductName} ({row.ProductCode})": row.ProductID
    for row in products.itertuples()
}

if auth.can_write("production"):
    with st.form("add_production_form", clear_on_submit=True):
        selected_label = st.selectbox("محصول *", list(product_options.keys()))
        c1, c2 = st.columns(2)
        with c1:
            serial_number = st.text_input("شماره سریال *")
            quantity = st.number_input(
                "مقدار تولیدشده *", min_value=0.0, step=1.0
            )
        with c2:
            st.caption("تاریخ تولید شمسی *")
            date_config = Config(
                locale="fa",
                selection_mode="single",
                default_value=jdatetime.date.today(),
            )
            picked_date = datepicker_component(config=date_config)
            if picked_date is None:
                picked_date = jdatetime.date.today()

        submitted = st.form_submit_button("ثبت تولید")
        if submitted:
            production_date = picked_date.strftime("%Y/%m/%d")

            if quantity <= 0:
                st.error("مقدار تولید باید بیشتر از صفر باشد.")
            elif not serial_number.strip():
                st.error("شماره سریال الزامی است.")
            else:
                product_id = product_options[selected_label]
                product_name = selected_label.split(" (")[0]
                ok, msg = dm.add_production(
                    product_id, product_name,
                    serial_number.strip(), quantity, production_date,
                    st.session_state.get("username")
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
else:
    st.info("شما فقط دسترسی مشاهده این بخش را دارید.")

st.subheader("تاریخچه تولید")
production_df = dm.load_sheet("Production")
if production_df.empty:
    st.info("هنوز تولیدی ثبت نشده است.")
else:
    st.dataframe(
        production_df.sort_values("ProductionID", ascending=False),
        use_container_width=True, hide_index=True
    )