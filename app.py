# -*- coding: utf-8 -*-
from pathlib import Path
import streamlit as st
import auth
import data_manager as dm

st.set_page_config(page_title="سامانه مدیریت انبار", page_icon="🏭", layout="wide")

auth.require_login()

pages_dir = Path(__file__).parent / "pages"
page_specs = [
    ("0_", "🏠 داشبورد", "dashboard"),
    ("1_", "📦 مدیریت محصولات", "products"),
    ("2_", "🏭 ثبت تولید", "production"),
    ("3_", "📤 ثبت خروج", "outbound"),
    ("4_", "🧾 فاکتور فروش", "sales_invoices"),
    ("5_", "📊 موجودی انبار", "inventory"),
    ("6_", "📋 برنامه‌ریزی تولید", "production_plan"),
    ("7_", "👤 مدیریت کاربران", "users"),
]

nav_pages = []
for prefix, title, permission_key in page_specs:
    matches = list(pages_dir.glob(prefix + "*.py"))
    if matches and auth.can_view(permission_key):
        nav_pages.append(st.Page(str(matches[0]), title=title))

if not nav_pages:
    st.error("هیچ بخشی برای حساب شما فعال نشده است. از مدیر سیستم بخواهید دسترسی بدهد.")
    st.stop()

st.navigation(nav_pages, position="sidebar").run()
