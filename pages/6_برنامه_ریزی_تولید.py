# -*- coding: utf-8 -*-
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="برنامه‌ریزی تولید", page_icon="📋", layout="wide")
auth.require_permission("production_plan")

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        📋 برنامه‌ریزی تولید روزانه
    </h1>
    """,
    unsafe_allow_html=True
)

lead_days = int(float(dm.get_setting("ProductionLeadDays", 7) or 7))
shipping_buffer = int(float(dm.get_setting("ShippingBufferDays", 2) or 2))


if auth.can_write("production_plan"):
    with st.expander("⚙️ تنظیمات برنامه‌ریزی", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            new_lead = st.number_input(
                "چند روز کاری قبل از موعد تولید شروع شود؟",
                min_value=0, value=lead_days, step=1
            )
        with c2:
            new_buffer = st.number_input(
                "چند روز کاری برای آماده‌سازی و ارسال کنار گذاشته شود؟",
                min_value=0, value=shipping_buffer, step=1
            )
        if st.button("ذخیره تنظیمات برنامه‌ریزی"):
            dm.set_setting("ProductionLeadDays", new_lead)
            dm.set_setting("ShippingBufferDays", new_buffer)
            st.success("تنظیمات ذخیره شد.")
            st.rerun()

plan = dm.compute_production_plan()
if plan.empty:
    st.info("برای فاکتورهای باز، برنامه‌ای برای نمایش وجود ندارد.")
    st.stop()

only_needed = st.checkbox(
    "فقط روزهایی که نیاز به تولید دارند", value=False
)
view = plan.copy()
if only_needed:
    view = view[view["تولید موردنیاز روز"] > 0]

st.dataframe(view, use_container_width=True, hide_index=True)

if not view.empty:
    warnings = view[view["وضعیت"].astype(str).str.contains("ظرفیت کافی", na=False)]
    if not warnings.empty:
        st.warning(
            "⚠️ برای بعضی سفارش‌ها ظرفیت تولید یا زمان کافی در بازه قبل از موعد وجود ندارد. "
            "ظرفیت روزانه محصول و موعد تحویل را بررسی کنید."
        )

csv = view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ دانلود برنامه روزانه CSV", data=csv,
    file_name="برنامه_ریزی_تولید_روزانه.csv", mime="text/csv"
)
