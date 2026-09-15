# -*- coding: utf-8 -*-
import json
import pandas as pd
import streamlit as st

import auth
import data_manager as dm

st.set_page_config(page_title="مدیریت کاربران", page_icon="👤", layout="wide")
auth.require_permission("users")

if not auth.is_admin():
    st.error("⛔ فقط مدیر سیستم به مدیریت کاربران دسترسی دارد.")
    st.stop()

st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        👤 مدیریت کاربران
    </h1>
    """,
    unsafe_allow_html=True
)

with st.expander("➕ افزودن کاربر جدید", expanded=True):
    with st.form("add_user_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("نام و نام خانوادگی *")
            username = st.text_input("نام کاربری *")
            password = st.text_input("رمز عبور *", type="password")
            password2 = st.text_input("تکرار رمز عبور *", type="password")
        with c2:
            is_admin = st.checkbox(
                "👑 مدیر سیستم / دسترسی کامل",
                help="مدیر سیستم همه بخش‌ها را می‌بیند و می‌تواند کاربر بسازد و دسترسی‌ها را تغییر دهد."
            )

        st.markdown("### دسترسی بخش‌ها")
        selected_permissions = dm.default_permissions()
        cols = st.columns(2)
        for i, (key, label) in enumerate(dm.PERMISSION_LABELS.items()):
            with cols[i % 2]:
                view = st.checkbox(f"مشاهده: {label}", key=f"new_view_{key}")
                write = st.checkbox(f"ثبت/ویرایش: {label}", key=f"new_write_{key}")
                selected_permissions[key] = {"view": view, "write": write}

        submitted = st.form_submit_button("ساخت کاربر")
        if submitted:
            if password != password2:
                st.error("رمزهای عبور یکسان نیستند.")
            elif not username.strip() or not name.strip():
                st.error("نام و نام کاربری الزامی است.")
            else:
                if is_admin:
                    selected_permissions = dm.full_permissions()
                ok, msg = auth.create_user(
                    username.strip(), name.strip(), password,
                    is_admin=is_admin, permissions=selected_permissions
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

st.subheader("کاربران موجود")
users = dm.load_sheet("Users")
if users.empty:
    st.info("کاربری ثبت نشده است.")
    st.stop()

for _, row in users.iterrows():
    username = str(row["Username"])
    display_name = str(row["Name"])
    row_is_admin = bool(row.get("IsAdmin", False))

    with st.expander(
        f"{'👑' if row_is_admin else '👤'} {display_name} — {username}"
    ):
        if username == st.session_state.get("username"):
            st.info("این حساب مدیر فعلی است.")

        with st.form(f"edit_{username}"):
            admin_new = st.checkbox(
                "مدیر سیستم / دسترسی کامل",
                value=row_is_admin,
                key=f"admin_{username}"
            )
            old_perms = dm.normalize_permissions(row.get("Permissions"))
            new_perms = {}

            cols = st.columns(2)
            for i, (key, label) in enumerate(dm.PERMISSION_LABELS.items()):
                with cols[i % 2]:
                    v = st.checkbox(
                        f"مشاهده: {label}",
                        value=old_perms[key]["view"],
                        key=f"v_{username}_{key}"
                    )
                    w = st.checkbox(
                        f"ثبت/ویرایش: {label}",
                        value=old_perms[key]["write"],
                        key=f"w_{username}_{key}"
                    )
                    new_perms[key] = {"view": v, "write": w}

            save = st.form_submit_button("ذخیره دسترسی‌ها")
            if save:
                if admin_new:
                    new_perms = dm.full_permissions()

                df = dm.load_sheet("Users")
                mask = df["Username"].astype(str) == username
                if mask.any():
                    df.loc[mask, "IsAdmin"] = admin_new
                    df.loc[mask, "Permissions"] = json.dumps(
                        new_perms, ensure_ascii=False
                    )
                    dm.save_sheet("Users", df)

                    # اگر مدیر فعلی تنظیمات خودش را تغییر داد، سشن هم به‌روز شود.
                    if username == st.session_state.get("username"):
                        st.session_state.is_admin = bool(admin_new)
                        st.session_state.permissions = new_perms

                    st.success("دسترسی‌ها ذخیره شد.")
                    st.rerun()

st.caption("رمز عبور کاربران به‌صورت هش‌شده ذخیره می‌شود و در جدول کاربران نمایش داده نمی‌شود.")
