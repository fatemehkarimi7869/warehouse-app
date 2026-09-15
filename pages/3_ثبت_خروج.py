# -*- coding: utf-8 -*-
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="ثبت خروج", page_icon="📤", layout="wide")
auth.require_permission("outbound")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        📤 ثبت خروج کالا از انبار
    </h1>
    """,
    unsafe_allow_html=True
)

products = dm.get_products()
production = dm.load_sheet("Production")

if products.empty:
    st.warning("ابتدا محصول تعریف کنید.")
    st.stop()

inventory = dm.compute_inventory()
stock_by_id = (
    dict(zip(inventory["ProductID"].astype(str), inventory["موجودی فعلی"]))
    if not inventory.empty else {}
)

product_options = {
    f"{row.ProductName} ({row.ProductCode}) — موجودی: {stock_by_id.get(str(row.ProductID), 0):g}":
        row.ProductID
    for row in products.itertuples()
}

if auth.can_write("outbound"):
    with st.form("add_outbound_form", clear_on_submit=True):
        selected_label = st.selectbox("محصول *", list(product_options.keys()))
        product_id = product_options[selected_label]

        prod_rows = production[
            production["ProductID"].astype(str) == str(product_id)
        ].copy()

        if prod_rows.empty:
            st.warning("برای این محصول هنوز تولیدی با بچ/سریال ثبت نشده است.")
            batch_options = []
        else:
            batch_options = []
            for _, r in prod_rows.iterrows():
                batch = str(r.get("BatchNumber", "") or "").strip()
                serial = str(r.get("SerialNumber", "") or "").strip()
                label = f"بچ: {batch or '-'} | سریال: {serial or '-'} | تولید: {r.get('Quantity', 0)}"
                batch_options.append((label, batch, serial))

        c1, c2 = st.columns(2)
        with c1:
            customer_name = st.text_input("نام مشتری *")
            quantity = st.number_input("مقدار خروجی *", min_value=0.0, step=1.0)
            invoice_number = st.text_input("شماره فاکتور فروش")
        with c2:
            outbound_date = st.text_input(
                "تاریخ خروج شمسی *", value=dm.jalali_today(),
                help="مثال: 1405/06/24"
            )
            province = st.text_input("استان *")
            city = st.text_input("شهر *")
            carrier_type = st.selectbox(
                "نوع باربری *",
                ["باربری", "پیک", "ماشین مشتری", "ماشین شرکت", "سایر"]
            )

        if batch_options:
            selected_batch = st.selectbox(
                "شماره بچ / سریال تولید *",
                batch_options,
                format_func=lambda x: x[0]
            )
        else:
            selected_batch = None

        submitted = st.form_submit_button("ثبت خروج")
        if submitted:
            try:
                dm.jalali_to_gregorian(outbound_date)
            except Exception as e:
                st.error(str(e))
                st.stop()

            current_stock = stock_by_id.get(str(product_id), 0)
            if quantity <= 0:
                st.error("مقدار خروج باید بیشتر از صفر باشد.")
            elif quantity > current_stock:
                st.error(
                    f"موجودی کافی نیست! موجودی فعلی: {current_stock:g}"
                )
            elif not customer_name.strip():
                st.error("نام مشتری الزامی است.")
            elif not province.strip() or not city.strip():
                st.error("استان و شهر الزامی است.")
            elif selected_batch is None:
                st.error("برای خروج باید یک بچ/سریال از سوابق تولید انتخاب کنید.")
            else:
                _, batch_number, serial_number = selected_batch
                product_name = selected_label.split(" (")[0]
                ok, msg = dm.add_outbound(
                    product_id, product_name, quantity, customer_name.strip(),
                    invoice_number.strip(), outbound_date.strip(),
                    province.strip(), city.strip(), carrier_type,
                    batch_number, serial_number,
                    st.session_state.get("username")
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
else:
    st.info("شما فقط دسترسی مشاهده این بخش را دارید.")

st.subheader("تاریخچه خروج")
outbound_df = dm.load_sheet("Outbound")
if outbound_df.empty:
    st.info("هنوز خروجی ثبت نشده است.")
else:
    st.dataframe(
        outbound_df.sort_values("OutboundID", ascending=False),
        use_container_width=True, hide_index=True
    )
