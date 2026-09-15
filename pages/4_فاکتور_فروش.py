# -*- coding: utf-8 -*-
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="فاکتور فروش", page_icon="🧾", layout="wide")
auth.require_permission("sales_invoices")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        🧾 ثبت فاکتور فروش
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

if auth.can_write("sales_invoices"):
    with st.form("add_invoice_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            invoice_number = st.text_input("شماره فاکتور *")
            selected_label = st.selectbox("محصول *", list(product_options.keys()))
            quantity = st.number_input("مقدار سفارش *", min_value=0.0, step=1.0)
            customer_name = st.text_input("نام مشتری *")
        with c2:
            sales_rep = st.text_input(
                "نام کارشناس فروش *",
                value=st.session_state.get("name") or ""
            )
            invoice_date = st.text_input(
                "تاریخ فاکتور شمسی *", value=dm.jalali_today(),
                help="مثال: 1405/06/24"
            )
            needed_date = st.text_input(
                "موعد تحویل به مشتری شمسی *", value=dm.jalali_today(),
                help="مثال: اگر امروز سفارش ثبت شده ولی قرار است ۲ هفته دیگر تحویل شود، تاریخ تحویل واقعی مشتری را وارد کنید."
            )

        submitted = st.form_submit_button("ثبت فاکتور")
        if submitted:
            try:
                dm.jalali_to_gregorian(invoice_date)
                dm.jalali_to_gregorian(needed_date)
            except Exception as e:
                st.error(str(e))
                st.stop()

            if not invoice_number.strip() or not customer_name.strip() or not sales_rep.strip():
                st.error("شماره فاکتور، مشتری و کارشناس فروش الزامی است.")
            elif not needed_date.strip():
                st.error("موعد تحویل مشتری الزامی است.")
            elif quantity <= 0:
                st.error("مقدار سفارش باید بیشتر از صفر باشد.")
            else:
                product_id = product_options[selected_label]
                product_name = selected_label.split(" (")[0]
                ok, msg = dm.add_sales_invoice(
                    invoice_number.strip(), product_id, product_name,
                    quantity, customer_name.strip(), sales_rep.strip(),
                    invoice_date.strip(), needed_date.strip()
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
else:
    st.info("شما فقط دسترسی مشاهده این بخش را دارید.")

st.subheader("فاکتورهای ثبت‌شده")
invoices = dm.load_sheet("SalesInvoices")
if invoices.empty:
    st.info("هنوز فاکتوری ثبت نشده است.")
else:
    status_filter = st.radio(
        "فیلتر وضعیت", ["همه", dm.STATUS_OPEN, dm.STATUS_FULFILLED],
        horizontal=True
    )
    view = invoices.sort_values("InvoiceID", ascending=False)
    if status_filter != "همه":
        view = view[view["Status"] == status_filter]
    st.dataframe(view, use_container_width=True, hide_index=True)
