# -*- coding: utf-8 -*-
"""
لایه مدیریت داده.
فعلاً اطلاعات در data/warehouse_data.xlsx ذخیره می‌شود.
"""
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "warehouse_data.xlsx"

SHEETS = {
    "Products": [
        "ProductID", "ProductCode", "ProductName", "Unit",
        "OpeningStock", "MinStock", "DailyProductionCapacity", "CreatedDate"
    ],
    "Production": [
        "ProductionID", "ProductID", "ProductName",
        "SerialNumber", "Quantity", "ProductionDate",
        "RegisteredBy", "RegisteredAt"
    ],
    "Outbound": [
        "OutboundID", "ProductID", "ProductName", "Quantity",
        "CustomerName", "InvoiceNumber", "OutboundDate",
        "Province", "City", "CarrierType", "BatchNumber",
        "SerialNumber", "RegisteredBy", "RegisteredAt"
    ],
    "SalesInvoices": [
        "InvoiceID", "InvoiceNumber", "ProductID", "ProductName",
        "Quantity", "CustomerName", "SalesRep", "InvoiceDate",
        "NeededDate", "Status", "RegisteredAt"
    ],
    "Settings": ["Setting", "Value"],
    "Users": [
        "Username", "Name", "PasswordHash", "IsAdmin",
        "Permissions", "CreatedAt"
    ],
}

STATUS_OPEN = "باز"
STATUS_FULFILLED = "تامین‌شده"

PERMISSION_LABELS = {
    "dashboard": "داشبورد",
    "products": "مدیریت محصولات",
    "production": "ثبت تولید",
    "outbound": "ثبت خروج",
    "sales_invoices": "فاکتور فروش",
    "inventory": "موجودی انبار",
    "production_plan": "برنامه‌ریزی تولید",
    "users": "مدیریت کاربران",
}


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_permissions():
    return {
        key: {"view": False, "write": False}
        for key in PERMISSION_LABELS
    }


def full_permissions():
    return {
        key: {"view": True, "write": True}
        for key in PERMISSION_LABELS
    }


def normalize_permissions(value):
    if isinstance(value, dict):
        result = default_permissions()
        for key in result:
            if isinstance(value.get(key), dict):
                result[key]["view"] = bool(value[key].get("view", False))
                result[key]["write"] = bool(value[key].get("write", False))
        return result
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default_permissions()
    try:
        return normalize_permissions(json.loads(str(value)))
    except Exception:
        return default_permissions()


def init_data_file():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as writer:
            for sheet, cols in SHEETS.items():
                pd.DataFrame(columns=cols).to_excel(
                    writer, sheet_name=sheet, index=False
                )


def load_all_sheets():
    init_data_file()
    sheets = pd.read_excel(DATA_FILE, sheet_name=None)
    changed = False

    for name, cols in SHEETS.items():
        if name not in sheets:
            sheets[name] = pd.DataFrame(columns=cols)
            changed = True
        else:
            for c in cols:
                if c not in sheets[name].columns:
                    sheets[name][c] = None
                    changed = True

    # مهاجرت خودکار فایل‌های نسخه قدیمی
    products = sheets["Products"]
    if "OpeningStock" in products.columns:
        products["OpeningStock"] = pd.to_numeric(
            products["OpeningStock"], errors="coerce"
        ).fillna(0)
        products["DailyProductionCapacity"] = pd.to_numeric(
            products.get("DailyProductionCapacity", 0), errors="coerce"
        ).fillna(0)
        sheets["Products"] = products

    settings = sheets["Settings"]
    defaults = {
        "ProductionLeadDays": "7",
        "ShippingBufferDays": "2",
    }
    for key, value in defaults.items():
        if settings.empty or key not in settings["Setting"].astype(str).values:
            settings = pd.concat([settings, pd.DataFrame([{
                "Setting": key, "Value": value
            }])], ignore_index=True)
            changed = True
    sheets["Settings"] = settings

    users = sheets["Users"]
    if not users.empty:
        if "IsAdmin" not in users.columns:
            users["IsAdmin"] = False
            changed = True
        if "Permissions" not in users.columns:
            users["Permissions"] = None
            changed = True

        # در نسخه قدیمی، اولین کاربر مدیر اصلی سیستم می‌شود.
        if not users["IsAdmin"].fillna(False).astype(bool).any():
            users.loc[users.index[0], "IsAdmin"] = True
            users.loc[users.index[0], "Permissions"] = json.dumps(
                full_permissions(), ensure_ascii=False
            )
            changed = True

        # مدیران همیشه دسترسی کامل دارند.
        for idx in users.index:
            if bool(users.at[idx, "IsAdmin"]):
                perms = json.dumps(full_permissions(), ensure_ascii=False)
                if str(users.at[idx, "Permissions"]) != perms:
                    users.at[idx, "Permissions"] = perms
                    changed = True
        sheets["Users"] = users

    if changed:
        save_all_sheets(sheets)
    return sheets


def save_all_sheets(sheets_dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as writer:
        for name, cols in SHEETS.items():
            df = sheets_dict.get(name, pd.DataFrame(columns=cols))
            df = df.reindex(columns=cols)
            df.to_excel(writer, sheet_name=name, index=False)


def load_sheet(name):
    sheets = load_all_sheets()
    return sheets.get(name, pd.DataFrame(columns=SHEETS[name])).copy()


def save_sheet(name, df):
    sheets = load_all_sheets()
    sheets[name] = df
    save_all_sheets(sheets)


def next_id(df, id_col):
    if df.empty:
        return 1
    ids = pd.to_numeric(df[id_col], errors="coerce").fillna(0)
    return int(ids.max()) + 1


def jalali_today():
    import jdatetime
    return jdatetime.date.today().strftime("%Y/%m/%d")


def jalali_to_gregorian(value):
    import jdatetime
    value = str(value or "").strip().replace("-", "/")
    parts = value.split("/")
    if len(parts) != 3:
        raise ValueError("تاریخ باید به شکل 1405/06/24 باشد.")
    y, m, d = [int(x) for x in parts]
    return jdatetime.date(y, m, d).togregorian()


def gregorian_to_jalali(value):
    import jdatetime
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return jdatetime.date.fromgregorian(
        date=dt.date()
    ).strftime("%Y/%m/%d")


def get_products():
    return load_sheet("Products")


def update_product_stock_settings(product_id, opening_stock, min_stock):
    df = load_sheet("Products")
    mask = df["ProductID"].astype(str) == str(product_id)
    if not mask.any():
        return False, "محصول پیدا نشد."
    df.loc[mask, "OpeningStock"] = opening_stock
    df.loc[mask, "MinStock"] = min_stock
    save_sheet("Products", df)
    return True, "موجودی اولیه و حداقل موجودی به‌روزرسانی شد."


def add_product(code, name, unit, opening_stock, min_stock, daily_capacity=0):
    df = load_sheet("Products")
    if code and str(code) in df["ProductCode"].astype(str).values:
        return False, "این کد محصول قبلاً ثبت شده است."

    new_row = {
        "ProductID": next_id(df, "ProductID"),
        "ProductCode": code,
        "ProductName": name,
        "Unit": unit,
        "OpeningStock": opening_stock,
        "MinStock": min_stock,
        "DailyProductionCapacity": daily_capacity,
        "CreatedDate": now_str(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet("Products", df)
    return True, "محصول با موفقیت اضافه شد."


def get_setting(name, default=None):
    df = load_sheet("Settings")
    if df.empty:
        return default
    match = df[df["Setting"].astype(str) == str(name)]
    if match.empty:
        return default
    return match.iloc[0]["Value"]


def set_setting(name, value):
    df = load_sheet("Settings")
    mask = df["Setting"].astype(str) == str(name)
    if mask.any():
        df.loc[mask, "Value"] = str(value)
    else:
        df = pd.concat([df, pd.DataFrame([{
            "Setting": name, "Value": str(value)
        }])], ignore_index=True)
    save_sheet("Settings", df)


def is_working_day(dt):
    # تقویم کاری ایران: جمعه تعطیل است. تعطیلات رسمی در این نسخه وارد نشده‌اند.
    return pd.Timestamp(dt).weekday() != 4


def working_days(start, end):
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    if end < start:
        return []
    return [d for d in pd.date_range(start, end, freq="D") if is_working_day(d)]


def subtract_working_days(date_value, days):
    d = pd.Timestamp(date_value).normalize()
    remaining = max(int(days), 0)
    while remaining:
        d -= pd.Timedelta(days=1)
        if is_working_day(d):
            remaining -= 1
    return d


def add_production(
    product_id, product_name, serial_number,
    quantity, production_date, registered_by
):
    df = load_sheet("Production")
    new_row = {
        "ProductionID": next_id(df, "ProductionID"),
        "ProductID": product_id,
        "ProductName": product_name,
        "SerialNumber": serial_number,
        "Quantity": quantity,
        "ProductionDate": production_date,
        "RegisteredBy": registered_by,
        "RegisteredAt": now_str(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet("Production", df)
    return True, "تولید با موفقیت ثبت شد."


def add_outbound(
    product_id, product_name, quantity, customer_name, invoice_number,
    outbound_date, province, city, carrier_type, batch_number,
    serial_number, registered_by
):
    # کنترل موجودی و در صورت انتخاب بچ/سریال، کنترل تولید مربوطه
    inventory = compute_inventory()
    stock = 0
    if not inventory.empty:
        row = inventory[
            inventory["ProductID"].astype(str) == str(product_id)
        ]
        if not row.empty:
            stock = float(row.iloc[0]["موجودی فعلی"])
    if quantity > stock:
        return False, f"موجودی کافی نیست. موجودی فعلی: {stock:g}"

    if serial_number:
        # توجه: شماره بچ دیگر در سوابق تولید ثبت نمی‌شود؛ تطبیق فقط با سریال انجام می‌شود.
        production = load_sheet("Production")
        mask = (
            (production["ProductID"].astype(str) == str(product_id))
            & (production["SerialNumber"].astype(str) == str(serial_number))
        )
        if not mask.any():
            return False, "سریال انتخاب‌شده در سوابق تولید این محصول پیدا نشد."

    df = load_sheet("Outbound")
    new_row = {
        "OutboundID": next_id(df, "OutboundID"),
        "ProductID": product_id,
        "ProductName": product_name,
        "Quantity": quantity,
        "CustomerName": customer_name,
        "InvoiceNumber": invoice_number,
        "OutboundDate": outbound_date,
        "Province": province,
        "City": city,
        "CarrierType": carrier_type,
        "BatchNumber": batch_number,
        "SerialNumber": serial_number,
        "RegisteredBy": registered_by,
        "RegisteredAt": now_str(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet("Outbound", df)

    if invoice_number:
        inv_df = load_sheet("SalesInvoices")
        mask = (
            inv_df["InvoiceNumber"].astype(str) == str(invoice_number)
        ) & (
            inv_df["ProductID"].astype(str) == str(product_id)
        )
        if mask.any():
            inv_df.loc[mask, "Status"] = STATUS_FULFILLED
            save_sheet("SalesInvoices", inv_df)

    return True, "خروج کالا با موفقیت ثبت شد."


def add_sales_invoice(
    invoice_number, product_id, product_name, quantity, customer_name,
    sales_rep, invoice_date, needed_date
):
    df = load_sheet("SalesInvoices")
    new_row = {
        "InvoiceID": next_id(df, "InvoiceID"),
        "InvoiceNumber": invoice_number,
        "ProductID": product_id,
        "ProductName": product_name,
        "Quantity": quantity,
        "CustomerName": customer_name,
        "SalesRep": sales_rep,
        "InvoiceDate": invoice_date,
        "NeededDate": needed_date,
        "Status": STATUS_OPEN,
        "RegisteredAt": now_str(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet("SalesInvoices", df)
    return True, "فاکتور فروش با موفقیت ثبت شد."


def compute_inventory():
    products = load_sheet("Products")
    production = load_sheet("Production")
    outbound = load_sheet("Outbound")

    cols = [
        "ProductID", "ProductCode", "ProductName", "Unit",
        "موجودی اولیه", "تولید کل", "خروج کل", "موجودی فعلی", "MinStock"
    ]
    if products.empty:
        return pd.DataFrame(columns=cols)

    products = products.copy()
    products["ProductID"] = products["ProductID"].astype(str)
    products["OpeningStock"] = pd.to_numeric(
        products["OpeningStock"], errors="coerce"
    ).fillna(0)
    products["MinStock"] = pd.to_numeric(
        products["MinStock"], errors="coerce"
    ).fillna(0)

    if production.empty:
        prod_sum = pd.Series(dtype=float)
    else:
        production["ProductID"] = production["ProductID"].astype(str)
        production["Quantity"] = pd.to_numeric(
            production["Quantity"], errors="coerce"
        ).fillna(0)
        prod_sum = production.groupby("ProductID")["Quantity"].sum()

    if outbound.empty:
        out_sum = pd.Series(dtype=float)
    else:
        outbound["ProductID"] = outbound["ProductID"].astype(str)
        outbound["Quantity"] = pd.to_numeric(
            outbound["Quantity"], errors="coerce"
        ).fillna(0)
        out_sum = outbound.groupby("ProductID")["Quantity"].sum()

    products["تولید کل"] = products["ProductID"].map(prod_sum).fillna(0)
    products["خروج کل"] = products["ProductID"].map(out_sum).fillna(0)
    products["موجودی اولیه"] = products["OpeningStock"]
    products["موجودی فعلی"] = (
        products["موجودی اولیه"] + products["تولید کل"] - products["خروج کل"]
    )

    return products[cols]


def compute_production_plan():
    """
    برنامه تولید روزانه بر اساس «موعد تحویل» است، نه تاریخ ثبت سفارش.
    برای هر سفارش باز، موجودی فعلی ابتدا برای نزدیک‌ترین موعد رزرو می‌شود.
    کسری سفارش در بازه قبل از موعد و با توجه به ظرفیت تولید روزانه محصول پخش می‌شود.
    جمعه به‌عنوان روز غیرکاری در نظر گرفته می‌شود.
    """
    inventory = compute_inventory()
    invoices = load_sheet("SalesInvoices")
    products = get_products()

    empty_cols = [
        "تاریخ تولید", "موعد تحویل", "ProductCode", "ProductName", "Unit",
        "سفارش مربوط", "تعداد سفارش", "موجودی قابل استفاده",
        "تولید برنامه‌ریزی‌شده", "تولید تجمعی تا امروز", "وضعیت"
    ]
    if inventory.empty or invoices.empty:
        return pd.DataFrame(columns=empty_cols)

    base = inventory.copy()
    base["ProductID"] = base["ProductID"].astype(str)
    inv = invoices.copy()
    inv["ProductID"] = inv["ProductID"].astype(str)
    inv["Quantity"] = pd.to_numeric(inv["Quantity"], errors="coerce").fillna(0)
    inv["Status"] = inv["Status"].fillna(STATUS_OPEN)
    inv = inv[inv["Status"] == STATUS_OPEN].copy()
    if inv.empty:
        return pd.DataFrame(columns=empty_cols)

    inv["موعد تحویل"] = inv["NeededDate"].apply(
        lambda x: pd.Timestamp(jalali_to_gregorian(x))
        if str(x).strip() not in ("", "nan", "None")
        else pd.NaT
    )
    # برای فاکتورهای قدیمی که موعد تحویل ندارند، به‌صورت موقت از تاریخ فاکتور استفاده می‌کنیم.
    missing_due = inv["موعد تحویل"].isna()
    if missing_due.any():
        inv.loc[missing_due, "موعد تحویل"] = inv.loc[missing_due, "InvoiceDate"].apply(
            lambda x: pd.Timestamp(jalali_to_gregorian(x))
            if str(x).strip() not in ("", "nan", "None") else pd.NaT
        )
    inv = inv.dropna(subset=["موعد تحویل"]).sort_values(["موعد تحویل", "InvoiceID"])

    today = pd.Timestamp(datetime.now().date()).normalize()
    try:
        lead_days = int(float(get_setting("ProductionLeadDays", 7)))
    except Exception:
        lead_days = 7
    try:
        shipping_buffer = int(float(get_setting("ShippingBufferDays", 2)))
    except Exception:
        shipping_buffer = 2

    capacity_map = {}
    if not products.empty:
        for _, r in products.iterrows():
            try:
                capacity_map[str(r["ProductID"])] = max(float(r.get("DailyProductionCapacity", 0) or 0), 0)
            except Exception:
                capacity_map[str(r["ProductID"])] = 0

    rows = []
    for pid, group in inv.groupby("ProductID", sort=False):
        product_row = base[base["ProductID"] == str(pid)]
        if product_row.empty:
            continue
        product = product_row.iloc[0]
        available_stock = max(float(product["موجودی فعلی"]), 0)
        capacity = capacity_map.get(str(pid), 0)
        scheduled_by_day = {}

        for _, order in group.iterrows():
            qty = float(order["Quantity"])
            due = pd.Timestamp(order["موعد تحویل"]).normalize()
            # موجودی فعلی/رزروشده برای نزدیک‌ترین موعد مصرف می‌شود.
            stock_for_order = min(available_stock, qty)
            available_stock -= stock_for_order
            required = max(qty - stock_for_order, 0)
            if required <= 0:
                rows.append({
                    "تاریخ تولید": "—",
                    "موعد تحویل": gregorian_to_jalali(due),
                    "ProductCode": product["ProductCode"],
                    "ProductName": product["ProductName"],
                    "Unit": product["Unit"],
                    "سفارش مربوط": order["InvoiceNumber"],
                    "تعداد سفارش": qty,
                    "موجودی قابل استفاده": stock_for_order,
                    "تولید برنامه‌ریزی‌شده": 0,
                    "تولید تجمعی تا امروز": 0,
                    "وضعیت": "با موجودی فعلی تأمین می‌شود",
                })
                continue

            # تولید باید قبل از موعد و قبل از زمان ارسال انجام شود.
            last_production_day = due
            if shipping_buffer > 0:
                last_production_day = subtract_working_days(due, shipping_buffer)
            start_day = max(today, subtract_working_days(last_production_day, lead_days - 1))

            days = working_days(start_day, last_production_day)
            if not days:
                days = [today] if today <= due and is_working_day(today) else [due]

            remaining = required
            # از نزدیک‌ترین روز به موعد به عقب برمی‌گردیم تا تولید دقیقاً در پنجره قبل از موعد پخش شود.
            for day in reversed(days):
                already = scheduled_by_day.get(day, 0)
                room = (capacity - already) if capacity > 0 else remaining
                if room <= 0:
                    continue
                amount = min(remaining, room)
                if amount > 0:
                    scheduled_by_day[day] = already + amount
                    rows.append({
                        "تاریخ تولید": gregorian_to_jalali(day),
                        "موعد تحویل": gregorian_to_jalali(due),
                        "ProductCode": product["ProductCode"],
                        "ProductName": product["ProductName"],
                        "Unit": product["Unit"],
                        "سفارش مربوط": order["InvoiceNumber"],
                        "تعداد سفارش": qty,
                        "موجودی قابل استفاده": stock_for_order,
                        "تولید برنامه‌ریزی‌شده": amount,
                        "تولید تجمعی تا امروز": 0,
                        "وضعیت": "برنامه‌ریزی‌شده",
                    })
                    remaining -= amount
                if remaining <= 0:
                    break

            if remaining > 0:
                # اگر ظرفیت/زمان کافی نبود، کمبود را به اولین روز مجاز منتقل می‌کنیم تا کاربر هشدار بگیرد.
                overflow_day = start_day
                scheduled_by_day[overflow_day] = scheduled_by_day.get(overflow_day, 0) + remaining
                rows.append({
                    "تاریخ تولید": gregorian_to_jalali(overflow_day),
                    "موعد تحویل": gregorian_to_jalali(due),
                    "ProductCode": product["ProductCode"],
                    "ProductName": product["ProductName"],
                    "Unit": product["Unit"],
                    "سفارش مربوط": order["InvoiceNumber"],
                    "تعداد سفارش": qty,
                    "موجودی قابل استفاده": stock_for_order,
                    "تولید برنامه‌ریزی‌شده": remaining,
                    "تولید تجمعی تا امروز": 0,
                    "وضعیت": "⚠️ ظرفیت کافی نیست / نیاز به بررسی",
                })

    result = pd.DataFrame(rows, columns=empty_cols)
    if result.empty:
        return result
    result["تاریخ_sort"] = result["تاریخ تولید"].apply(
        lambda x: pd.Timestamp(jalali_to_gregorian(x)) if x != "—" else pd.Timestamp.max
    )
    result["موعد_sort"] = result["موعد تحویل"].apply(lambda x: pd.Timestamp(jalali_to_gregorian(x)))
    result = result.sort_values(["تاریخ_sort", "موعد_sort", "ProductCode"]).drop(columns=["تاریخ_sort", "موعد_sort"])
    return result.reset_index(drop=True)


def export_to_excel_bytes():
    import io

    sheets = load_all_sheets()
    inventory = compute_inventory()
    plan = compute_production_plan()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        inventory.to_excel(writer, sheet_name="موجودی انبار", index=False)
        plan.to_excel(writer, sheet_name="برنامه‌ریزی تولید", index=False)
        for name in SHEETS:
            sheets[name].to_excel(writer, sheet_name=name, index=False)
    buffer.seek(0)
    return buffer