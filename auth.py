# -*- coding: utf-8 -*-
import json
import bcrypt
import pandas as pd
import streamlit as st

import data_manager as dm


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), str(hashed).encode("utf-8")
        )
    except Exception:
        return False


def create_user(username, name, password, is_admin=False, permissions=None):
    username = (username or "").strip()
    if not username or not password:
        return False, "نام کاربری و رمز عبور الزامی است."

    df = dm.load_sheet("Users")
    if not df.empty and username in df["Username"].astype(str).values:
        return False, "این نام کاربری قبلاً استفاده شده است."

    if is_admin:
        permissions = dm.full_permissions()
    else:
        permissions = permissions or dm.default_permissions()

    new_row = {
        "Username": username,
        "Name": name or username,
        "PasswordHash": hash_password(password),
        "IsAdmin": bool(is_admin),
        "Permissions": json.dumps(permissions, ensure_ascii=False),
        "CreatedAt": dm.now_str(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    dm.save_sheet("Users", df)
    return True, "کاربر با موفقیت ساخته شد."


def get_user(username):
    df = dm.load_sheet("Users")
    if df.empty:
        return None

    match = df[df["Username"].astype(str) == str(username).strip()]
    if match.empty:
        return None

    row = match.iloc[0]
    return {
        "Username": str(row["Username"]),
        "Name": str(row["Name"]),
        "IsAdmin": bool(row.get("IsAdmin", False)),
        "Permissions": dm.normalize_permissions(row.get("Permissions")),
    }


def authenticate(username, password):
    df = dm.load_sheet("Users")
    if df.empty:
        return False, None

    match = df[df["Username"].astype(str) == str(username).strip()]
    if match.empty:
        return False, None

    row = match.iloc[0]
    if verify_password(password, row["PasswordHash"]):
        return True, {
            "username": str(row["Username"]),
            "name": str(row["Name"]),
            "is_admin": bool(row.get("IsAdmin", False)),
            "permissions": dm.normalize_permissions(row.get("Permissions")),
        }
    return False, None


def is_admin():
    return bool(st.session_state.get("is_admin", False))


def can_view(page_key):
    if is_admin():
        return True
    perms = st.session_state.get("permissions", {})
    return bool(perms.get(page_key, {}).get("view", False))


def can_write(page_key):
    if is_admin():
        return True
    perms = st.session_state.get("permissions", {})
    return bool(perms.get(page_key, {}).get("write", False))


def require_permission(page_key, write=False):
    require_login()
    allowed = can_write(page_key) if write else can_view(page_key)
    if not allowed:
        st.error("⛔ شما برای این بخش دسترسی ندارید.")
        st.stop()


def apply_rtl_style():
    st.markdown(
        """
        <style>
        html, body, [class*="css"], [class*="st-"] {
            direction: rtl;
        }
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div, .stTextArea textarea {
            direction: rtl;
            text-align: right;
        }
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
            direction: rtl;
        }
        thead tr th { text-align: right !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logout():
    for key in [
        "authenticated", "username", "name",
        "is_admin", "permissions"
    ]:
        st.session_state[key] = None
    st.session_state["authenticated"] = False
    st.rerun()


def require_login():
    apply_rtl_style()

    if st.session_state.get("authenticated"):
        with st.sidebar:
            role = "مدیر سیستم" if is_admin() else "کاربر"
            st.success(
                f"👤 {st.session_state.get('name') or st.session_state.get('username')}"
                f"\n\n{role}"
            )
            if st.button("🚪 خروج از حساب"):
                logout()
        return True

    st.markdown(
    """
    <h1 style="text-align: right; direction: rtl;">
        🏭 ورود به سامانه مدیریت انبار
    </h1>
    """,
    unsafe_allow_html=True
)
    
    users_df = dm.load_sheet("Users")

    # فقط اولین کاربر در نصب اولیه می‌تواند مدیر اصلی شود.
    if users_df.empty:
        st.info(
            "هنوز هیچ کاربری وجود ندارد. این فرم فقط برای ساخت اولین مدیر سیستم است."
        )
        with st.form("create_first_user"):
            name = st.text_input("نام و نام خانوادگی")
            username = st.text_input("نام کاربری")
            password = st.text_input("رمز عبور", type="password")
            password2 = st.text_input("تکرار رمز عبور", type="password")
            submitted = st.form_submit_button("ساخت مدیر اصلی")
            if submitted:
                if password != password2:
                    st.error("رمزهای عبور یکسان نیستند.")
                else:
                    ok, msg = create_user(
                        username, name, password,
                        is_admin=True,
                        permissions=dm.full_permissions(),
                    )
                    if ok:
                        st.success("مدیر اصلی ساخته شد. اکنون وارد شوید.")
                        st.rerun()
                    else:
                        st.error(msg)
        st.stop()

    with st.form("login_form"):
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        submitted = st.form_submit_button("ورود")
        if submitted:
            ok, user = authenticate(username, password)
            if ok:
                st.session_state.authenticated = True
                st.session_state.username = user["username"]
                st.session_state.name = user["name"]
                st.session_state.is_admin = user["is_admin"]
                st.session_state.permissions = user["permissions"]
                st.rerun()
            else:
                st.error("نام کاربری یا رمز عبور اشتباه است.")
    st.stop()
