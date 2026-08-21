import io
import sqlite3
import urllib.parse
import hashlib
import hmac
import secrets as py_secrets
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

import streamlit as st


# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="MS MAA VINDHYAWASINI TRADERS (COCA COLA)",
    page_icon="🥤",
    layout="wide",
)


# ==============================================================================
# 🔐 LOGIN / AUTHENTICATION SYSTEM
# ==============================================================================

def hash_password(password, salt):
    """
    Secure PBKDF2-HMAC-SHA256 password hashing.
    """
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        300_000,
    ).hex()


def verify_password(password, stored_hash, stored_salt):
    """
    Verify entered password against stored hash.
    """
    try:
        salt = bytes.fromhex(stored_salt)

        calculated_hash = hash_password(
            password,
            salt,
        )

        return hmac.compare_digest(
            calculated_hash,
            stored_hash,
        )

    except Exception:
        return False


def login_screen():

    st.markdown(
        """
        <style>
        .login-box {
            max-width: 460px;
            margin: 80px auto 20px auto;
            padding: 30px;
            border-radius: 16px;
            background: white;
            box-shadow: 0 5px 25px rgba(0,0,0,0.12);
            border-top: 6px solid #DC2626;
        }

        .login-title {
            text-align: center;
            color: #111827;
            font-size: 25px;
            font-weight: 700;
        }

        .login-subtitle {
            text-align: center;
            color: #64748B;
            margin-top: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="login-box">
            <div class="login-title">
                🥤 MS MAA VINDHYAWASINI TRADERS
            </div>
            <div class="login-subtitle">
                🔐 Secure Business Login
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, login_col, _ = st.columns([1, 2, 1])

    with login_col:

        username = st.text_input(
            "👤 Username",
            placeholder="Enter username",
            key="login_username",
        )

        password = st.text_input(
            "🔑 Password",
            type="password",
            placeholder="Enter password",
            key="login_password",
        )

        if st.button(
            "🔐 LOGIN",
            use_container_width=True,
            type="primary",
        ):

            username_clean = username.strip().lower()

            try:
                users = st.secrets["users"]
                user = users.get(username_clean)
            except Exception:
                user = None

            if user:

                stored_hash = user.get(
                    "password_hash",
                    "",
                )

                stored_salt = user.get(
                    "password_salt",
                    "",
                )

                if verify_password(
                    password,
                    stored_hash,
                    stored_salt,
                ):

                    st.session_state[
                        "authenticated"
                    ] = True

                    st.session_state[
                        "username"
                    ] = username_clean

                    st.session_state[
                        "role"
                    ] = user.get(
                        "role",
                        "staff",
                    )

                    st.rerun()

            st.error(
                "❌ Invalid username or password."
            )


# ==============================================================================
# 🔒 LOGIN GATE
# ==============================================================================

if not st.session_state.get(
    "authenticated",
    False,
):

    login_screen()
    st.stop()


# ==============================================================================
# CUSTOM STYLES
# ==============================================================================

st.markdown(
    """
    <style>
    .red-card {
        background-color: #FFEBEB;
        border-left: 6px solid #D9534F;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .green-card {
        background-color: #EBF9EB;
        border-left: 6px solid #5CB85C;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .edit-card {
        background-color: #FFF8E1;
        border-left: 6px solid #F0AD4E;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .delete-card {
        background-color: #FFF1F2;
        border-left: 6px solid #DC2626;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# APP HEADER
# ==============================================================================

st.title("🥤 MS MAA VINDHYAWASINI TRADERS (COCA COLA)")

st.caption(
    "Bill-Wise Ledger System - Auto Generated Bill Code (NAME + SERIAL NO)"
)


# ==============================================================================
# DATABASE
# ==============================================================================

DB_FILE = "khatabook_billwise_v6.db"


def get_connection():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30,
    )

    return conn


def init_db():

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS bills (
            Bill_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Bill_No TEXT UNIQUE,
            Date TEXT,
            Manager_Name TEXT,
            Outlet_Name TEXT,
            Bill_Amount REAL,
            Paid_Amount REAL,
            Balance REAL,
            Status TEXT,
            Note TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            Payment_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT,
            Bill_No TEXT,
            Outlet_Name TEXT,
            Manager_Name TEXT,
            Amount_Paid REAL,
            Payment_Mode TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS managers (
            name TEXT PRIMARY KEY
        )
        """
    )

    c.execute(
        """
        INSERT OR IGNORE INTO managers (name)
        VALUES ('Default Manager')
        """
    )

    conn.commit()
    conn.close()


def get_all_bills():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM bills
        ORDER BY Bill_ID DESC
        """,
        conn,
    )

    conn.close()

    return df


def get_all_payments():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM payments
        ORDER BY Payment_ID DESC
        """,
        conn,
    )

    conn.close()

    return df


def get_managers():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT name
        FROM managers
        ORDER BY name ASC
        """,
        conn,
    )

    conn.close()

    if not df.empty:
        return df["name"].tolist()

    return ["Default Manager"]


def get_outlets():

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT DISTINCT Outlet_Name
        FROM bills
        ORDER BY Outlet_Name ASC
        """
    )

    outlets = [
        row[0]
        for row in c.fetchall()
        if row[0]
    ]

    conn.close()

    return outlets


# ==============================================================================
# AUTO BILL CODE GENERATOR
# ==============================================================================

def generate_auto_code_backend(outlet_name):

    clean_name = (
        "".join(
            e
            for e in outlet_name
            if e.isalnum()
        ).upper()
        if outlet_name
        else "BILL"
    )

    if not clean_name:
        clean_name = "BILL"

    short_code = clean_name[:5]

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)
        FROM bills
        WHERE Outlet_Name = ?
        """,
        (outlet_name.strip(),),
    )

    count = c.fetchone()[0] + 1

    conn.close()

    return f"{short_code}-{count}"


# ==============================================================================
# SAVE NEW BILL
# ==============================================================================

def save_bill_to_db(
    date_str,
    mgr,
    outlet,
    amount,
    note,
):

    conn = get_connection()
    c = conn.cursor()

    try:

        # Generate code inside same connection
        clean_name = outlet.strip()

        clean_code_name = "".join(
            e
            for e in clean_name
            if e.isalnum()
        ).upper()

        if not clean_code_name:
            clean_code_name = "BILL"

        short_code = clean_code_name[:5]

        c.execute(
            """
            SELECT COUNT(*)
            FROM bills
            WHERE Outlet_Name = ?
            """,
            (clean_name,),
        )

        count = c.fetchone()[0] + 1

        bill_no = f"{short_code}-{count}"

        # Extra protection against duplicate bill code
        c.execute(
            """
            SELECT 1
            FROM bills
            WHERE Bill_No = ?
            """,
            (bill_no,),
        )

        if c.fetchone():

            count += 1
            bill_no = f"{short_code}-{count}"

        c.execute(
            """
            INSERT INTO bills (
                Bill_No,
                Date,
                Manager_Name,
                Outlet_Name,
                Bill_Amount,
                Paid_Amount,
                Balance,
                Status,
                Note
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                0.0,
                ?,
                '🔴 UNPAID',
                ?
            )
            """,
            (
                bill_no,
                date_str,
                mgr,
                clean_name,
                amount,
                amount,
                note,
            ),
        )

        conn.commit()

        return bill_no

    except sqlite3.IntegrityError:

        conn.rollback()

        # Fallback unique code
        bill_no = (
            f"{short_code}-"
            f"{int(datetime.now().timestamp())}"
        )

        c.execute(
            """
            INSERT INTO bills (
                Bill_No,
                Date,
                Manager_Name,
                Outlet_Name,
                Bill_Amount,
                Paid_Amount,
                Balance,
                Status,
                Note
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                0.0,
                ?,
                '🔴 UNPAID',
                ?
            )
            """,
            (
                bill_no,
                date_str,
                mgr,
                clean_name,
                amount,
                amount,
                note,
            ),
        )

        conn.commit()

        return bill_no

    finally:

        conn.close()


# ==============================================================================
# UPDATE BILL
# ==============================================================================

def update_bill_in_db(
    bill_no,
    date_str,
    mgr,
    outlet,
    amount,
    note,
):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT Paid_Amount
        FROM bills
        WHERE Bill_No = ?
        """,
        (bill_no,),
    )

    row = c.fetchone()

    if not row:

        conn.close()

        return False, "Bill not found."

    paid_amount = float(row[0])

    if amount < paid_amount:

        conn.close()

        return (
            False,
            f"Bill amount cannot be less than already paid "
            f"amount Rs {paid_amount:,.2f}.",
        )

    balance = amount - paid_amount

    if balance <= 0:

        status = "🟢 PAID"
        balance = 0.0

    elif paid_amount > 0:

        status = "🔴 PARTIAL"

    else:

        status = "🔴 UNPAID"

    c.execute(
        """
        UPDATE bills
        SET
            Date = ?,
            Manager_Name = ?,
            Outlet_Name = ?,
            Bill_Amount = ?,
            Balance = ?,
            Status = ?,
            Note = ?
        WHERE Bill_No = ?
        """,
        (
            date_str,
            mgr,
            outlet,
            amount,
            balance,
            status,
            note,
            bill_no,
        ),
    )

    c.execute(
        """
        UPDATE payments
        SET
            Outlet_Name = ?,
            Manager_Name = ?
        WHERE Bill_No = ?
        """,
        (
            outlet,
            mgr,
            bill_no,
        ),
    )

    conn.commit()
    conn.close()

    return True, "Bill updated successfully."


# ==============================================================================
# RECORD PAYMENT
# ==============================================================================

def record_bill_payment(
    bill_no,
    date_str,
    outlet,
    mgr,
    paid_amt,
    mode,
    is_full,
):

    conn = get_connection()
    c = conn.cursor()

    try:

        c.execute(
            """
            SELECT
                Bill_Amount,
                Paid_Amount,
                Balance
            FROM bills
            WHERE Bill_No = ?
            """,
            (bill_no,),
        )

        row = c.fetchone()

        if not row:
            return False, "Bill not found."

        bill_amt, curr_paid, curr_bal = row

        bill_amt = float(bill_amt)
        curr_paid = float(curr_paid)
        curr_bal = float(curr_bal)

        if curr_bal <= 0:
            return False, "This bill is already fully paid."

        if is_full:

            actual_payment = curr_bal

        else:

            if paid_amt <= 0:
                return False, "Payment amount must be greater than zero."

            if paid_amt > curr_bal:
                return False, "Payment cannot exceed outstanding balance."

            actual_payment = paid_amt

        new_paid = curr_paid + actual_payment
        new_bal = bill_amt - new_paid

        if new_bal <= 0:

            new_status = "🟢 PAID"
            new_bal = 0.0

        else:

            new_status = "🔴 PARTIAL"

        c.execute(
            """
            UPDATE bills
            SET
                Paid_Amount = ?,
                Balance = ?,
                Status = ?
            WHERE Bill_No = ?
            """,
            (
                new_paid,
                new_bal,
                new_status,
                bill_no,
            ),
        )

        c.execute(
            """
            INSERT INTO payments (
                Date,
                Bill_No,
                Outlet_Name,
                Manager_Name,
                Amount_Paid,
                Payment_Mode
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                bill_no,
                outlet,
                mgr,
                actual_payment,
                mode,
            ),
        )

        conn.commit()

        return True, actual_payment

    except Exception as e:

        conn.rollback()

        return False, str(e)

    finally:

        conn.close()


# ==============================================================================
# DELETE BILL - ADMIN ONLY
# ==============================================================================

def delete_bill_from_db(bill_no):

    conn = get_connection()
    c = conn.cursor()

    try:

        c.execute(
            """
            DELETE FROM payments
            WHERE Bill_No = ?
            """,
            (bill_no,),
        )

        c.execute(
            """
            DELETE FROM bills
            WHERE Bill_No = ?
            """,
            (bill_no,),
        )

        conn.commit()

    finally:

        conn.close()


# ==============================================================================
# DELETE PAYMENT - ADMIN ONLY
# IMPORTANT: Paid amount is recalculated from remaining payment records.
# ==============================================================================

def delete_payment_from_db(pay_id, bill_no):

    conn = get_connection()
    c = conn.cursor()

    try:

        c.execute(
            """
            DELETE FROM payments
            WHERE Payment_ID = ?
            AND Bill_No = ?
            """,
            (
                pay_id,
                bill_no,
            ),
        )

        c.execute(
            """
            SELECT
                Bill_Amount
            FROM bills
            WHERE Bill_No = ?
            """,
            (bill_no,),
        )

        bill_row = c.fetchone()

        if bill_row:

            bill_amount = float(
                bill_row[0]
            )

            c.execute(
                """
                SELECT
                    COALESCE(
                        SUM(Amount_Paid),
                        0
                    )
                FROM payments
                WHERE Bill_No = ?
                """,
                (bill_no,),
            )

            total_paid = float(
                c.fetchone()[0]
            )

            balance = bill_amount - total_paid

            if balance <= 0:

                balance = 0.0
                status = "🟢 PAID"

            elif total_paid <= 0:

                total_paid = 0.0
                status = "🔴 UNPAID"

            else:

                status = "🔴 PARTIAL"

            c.execute(
                """
                UPDATE bills
                SET
                    Paid_Amount = ?,
                    Balance = ?,
                    Status = ?
                WHERE Bill_No = ?
                """,
                (
                    total_paid,
                    balance,
                    status,
                    bill_no,
                ),
            )

        conn.commit()

    finally:

        conn.close()


# ==============================================================================
# SAVE MANAGER
# ==============================================================================

def save_manager_to_db(mgr_str):

    clean_mgr = mgr_str.strip().title()

    if clean_mgr:

        conn = get_connection()
        c = conn.cursor()

        c.execute(
            """
            INSERT OR IGNORE INTO managers (name)
            VALUES (?)
            """,
            (clean_mgr,),
        )

        conn.commit()
        conn.close()


# ==============================================================================
# INITIALIZE DATABASE
# ==============================================================================

init_db()


# ==============================================================================
# DAYS PENDING
# ==============================================================================

def calculate_days_pending(bill_date_str):

    try:

        b_date = datetime.strptime(
            bill_date_str,
            "%d-%m-%Y",
        )

        days = (
            datetime.now() - b_date
        ).days

        return max(0, days)

    except Exception:

        return 0


# ==============================================================================
# PDF REPORT
# ==============================================================================

def generate_pdf_report(
    df_data,
    subtitle_info="",
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=25,
        bottomMargin=25,
    )

    elements = []

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )

    sub_title_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#B91C1C"),
        fontName="Helvetica-Bold",
        spaceAfter=8,
    )

    outlet_style = ParagraphStyle(
        "OutletTitle",
        parent=styles["Normal"],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        spaceAfter=5,
    )

    info_style = ParagraphStyle(
        "DocInfo",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )

    table_hdr_style = ParagraphStyle(
        "TableHdr",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )

    red_status_style = ParagraphStyle(
        "RedStatus",
        parent=table_cell_style,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold",
    )

    green_status_style = ParagraphStyle(
        "GreenStatus",
        parent=table_cell_style,
        textColor=colors.HexColor("#16A34A"),
        fontName="Helvetica-Bold",
    )

    red_balance_style = ParagraphStyle(
        "RedBalance",
        parent=table_cell_style,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold",
    )

    green_amount_style = ParagraphStyle(
        "GreenAmount",
        parent=table_cell_style,
        textColor=colors.HexColor("#16A34A"),
        fontName="Helvetica-Bold",
    )

    total_dues_style = ParagraphStyle(
        "TotalDues",
        parent=styles["Normal"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold",
        alignment=2,
        spaceBefore=10,
        spaceAfter=5,
    )

    elements.append(
        Paragraph(
            "🥤 MS MAA VINDHYAWASINI TRADERS",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "AUTHORIZED COCA-COLA DISTRIBUTOR",
            sub_title_style,
        )
    )

    outlet_name_for_pdf = ""

    if "Outlet:" in subtitle_info:

        try:

            outlet_name_for_pdf = (
                subtitle_info
                .split("Outlet:", 1)[1]
                .split("|", 1)[0]
                .strip()
            )

        except Exception:

            outlet_name_for_pdf = ""

    if not outlet_name_for_pdf:

        outlet_name_for_pdf = "All Outlets"

    elements.append(
        Paragraph(
            f"OUTLET: {outlet_name_for_pdf}",
            outlet_style,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Statement Info:</b> {subtitle_info} | "
            f"<b>Generated:</b> "
            f"{datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
            info_style,
        )
    )

    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#DC2626"),
            spaceAfter=10,
        )
    )

    headers = [
        "Bill Code",
        "Date",
        "Outlet/Customer",
        "Bill Amt (Rs)",
        "Paid Amt (Rs)",
        "Balance (Rs)",
        "Status",
    ]

    table_data = [
        [
            Paragraph(
                h,
                table_hdr_style,
            )
            for h in headers
        ]
    ]

    for _, row in df_data.iterrows():

        status = str(row["Status"])

        if (
            "PAID" in status
            and "UNPAID" not in status
        ):

            status_style = green_status_style

        else:

            status_style = red_status_style

        if float(row["Balance"]) > 0:

            balance_style = red_balance_style

        else:

            balance_style = green_status_style

        table_data.append(
            [
                Paragraph(
                    str(row["Bill_No"]),
                    table_cell_style,
                ),

                Paragraph(
                    str(row["Date"]),
                    table_cell_style,
                ),

                Paragraph(
                    str(row["Outlet_Name"]),
                    table_cell_style,
                ),

                Paragraph(
                    f"Rs {row['Bill_Amount']:,.2f}",
                    table_cell_style,
                ),

                Paragraph(
                    f"Rs {row['Paid_Amount']:,.2f}",
                    green_amount_style,
                ),

                Paragraph(
                    f"Rs {row['Balance']:,.2f}",
                    balance_style,
                ),

                Paragraph(
                    status,
                    status_style,
                ),
            ]
        )

    t = Table(
        table_data,
        colWidths=[
            70,
            65,
            125,
            70,
            70,
            75,
            70,
        ],
        repeatRows=1,
    )

    t.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1E293B"),
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, 0),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (0, 1),
                    (-1, -1),
                    "LEFT",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    elements.append(t)

    total_net_dues = float(
        df_data["Balance"].sum()
    )

    elements.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#CBD5E1"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )

    elements.append(
        Paragraph(
            f"TOTAL NET DUES: Rs {total_net_dues:,.2f}",
            total_dues_style,
        )
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        alignment=2,
        spaceBefore=5,
    )

    elements.append(
        Paragraph(
            "This is a computer generated statement.",
            footer_style,
        )
    )

    doc.build(elements)

    buffer.seek(0)

    return buffer.getvalue()


# ==============================================================================
# FETCH DATA
# ==============================================================================

managers_list = get_managers()
outlets_list = get_outlets()
bills_df = get_all_bills()
payments_df = get_all_payments()


# ==============================================================================
# SIDEBAR
# ==============================================================================

with st.sidebar:

    st.header("⚙️ Master Settings")

    current_username = st.session_state.get(
        "username",
        "Unknown",
    )

    current_role = st.session_state.get(
        "role",
        "staff",
    )

    st.success(
        f"👤 Logged in: {current_username}"
    )

    st.caption(
        f"Role: {current_role.upper()}"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True,
    ):

        for key in [
            "authenticated",
            "username",
            "role",
        ]:

            st.session_state.pop(
                key,
                None,
            )

        st.rerun()

    st.divider()

    # --------------------------------------------------------------------------
    # MANAGER SETUP
    # --------------------------------------------------------------------------

    with st.expander("👤 Manager Setup"):

        new_mgr = st.text_input(
            "Add New Sales Manager"
        )

        if st.button(
            "Save Manager"
        ):

            if new_mgr.strip():

                save_manager_to_db(
                    new_mgr
                )

                st.success(
                    f"Added Manager: {new_mgr}"
                )

                st.rerun()

        st.divider()

        st.write("**Current Managers:**")

        st.write(
            ", ".join(managers_list)
        )

    # --------------------------------------------------------------------------
    # BACKUP
    # --------------------------------------------------------------------------

    with st.expander("💾 Backup CSV"):

        if not bills_df.empty:

            csv_buf = (
                bills_df
                .to_csv(index=False)
                .encode("utf-8")
            )

            st.download_button(
                label="📥 Download Bills CSV Backup",
                data=csv_buf,
                file_name=(
                    "maa_vindhyawasini_bills_"
                    f"{datetime.now().strftime('%d-%m-%Y')}.csv"
                ),
                mime="text/csv",
            )


# ==============================================================================
# TRANSACTIONS
# ==============================================================================

st.markdown("---")

col_left, col_right = st.columns(2)


# ==============================================================================
# CREATE NEW BILL
# ==============================================================================

with col_left:

    st.markdown(
        """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">
                🔴 CREATE NEW BILL / DUES
            </h3>
            <p style="margin:0; font-size:13px; color:#555;">
                Record new bill entry against Outlet
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b_date = st.date_input(
        "Bill Date",
        datetime.now(),
        format="DD/MM/YYYY",
        key="b_date_key",
    )

    b_manager = st.selectbox(
        "Select Sales Manager",
        managers_list,
        key="b_mgr_select",
    )

    existing_outlets = [
        "+ Add New Customer/Outlet"
    ] + outlets_list

    selected_b_outlet = st.selectbox(
        "Customer / Outlet Name",
        existing_outlets,
        key="b_outlet_select",
    )

    if (
        selected_b_outlet
        == "+ Add New Customer/Outlet"
    ):

        b_outlet = st.text_input(
            "Enter Store Name (दुकान का नाम)",
            placeholder="e.g. RAM TRADERS",
            key="b_outlet_text",
        )

    else:

        b_outlet = selected_b_outlet

    st.info(
        "💡 Bill Code (जैसे: RAM-1, RAHUL-2) "
        "ऑटोमैटिक जेनरेट हो जाएगा।"
    )

    b_amount = st.number_input(
        "Bill Amount (Rs)",
        min_value=0.0,
        step=50.0,
        key="b_amt",
    )

    b_note = st.text_input(
        "Bill Details / Goods Note (Optional)",
        key="b_note",
    )

    if st.button(
        "🔴 Save Bill Entry",
        use_container_width=True,
    ):

        if not b_outlet.strip():

            st.error(
                "Please enter a valid Outlet Name!"
            )

        elif b_amount <= 0:

            st.error(
                "Please enter a valid amount greater than zero!"
            )

        else:

            final_outlet = (
                b_outlet
                .strip()
                .title()
            )

            formatted_date = (
                b_date.strftime("%d-%m-%Y")
            )

            created_code = save_bill_to_db(
                formatted_date,
                b_manager,
                final_outlet,
                float(b_amount),
                (
                    b_note
                    if b_note
                    else "Coca Cola Goods Bill"
                ),
            )

            st.success(
                f"🔴 Created Bill '{created_code}' "
                f"for {final_outlet} of "
                f"Rs {b_amount:,.2f}"
            )

            st.rerun()


# ==============================================================================
# PAYMENT RECEIVED
# ==============================================================================

with col_right:

    st.markdown(
        """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">
                🟢 BILL-WISE PAYMENT RECEIVED
            </h3>
            <p style="margin:0; font-size:13px; color:#555;">
                Clear Full or Partial Payment against specific Bill
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not outlets_list:

        st.info(
            "No active outlets found. "
            "Create a bill on the left first."
        )

    else:

        p_outlet = st.selectbox(
            "Select Customer / Outlet for Payment:",
            outlets_list,
            key="p_outlet_select",
        )

        conn = get_connection()

        unpaid_bills_df = pd.read_sql_query(
            """
            SELECT *
            FROM bills
            WHERE Outlet_Name = ?
            AND Balance > 0
            ORDER BY Bill_ID ASC
            """,
            conn,
            params=(p_outlet,),
        )

        conn.close()

        if unpaid_bills_df.empty:

            st.success(
                f"🎉 No outstanding unpaid bills for "
                f"{p_outlet}!"
            )

        else:

            bill_options = {}

            for _, row in unpaid_bills_df.iterrows():

                d_days = calculate_days_pending(
                    row["Date"]
                )

                label = (
                    f"{row['Bill_No']} | "
                    f"Date: {row['Date']} | "
                    f"⏰ {d_days} Days Old | "
                    f"Balance Due: "
                    f"Rs {row['Balance']:,.2f}"
                )

                bill_options[label] = row

            selected_bill_label = st.selectbox(
                "Select Pending Bill Code to Clear Payment:",
                list(bill_options.keys()),
            )

            selected_bill = bill_options[
                selected_bill_label
            ]

            p_date = st.date_input(
                "Payment Date",
                datetime.now(),
                format="DD/MM/YYYY",
                key="p_date_key",
            )

            pay_type = st.radio(
                "Payment Type (भुगतान का प्रकार):",
                [
                    "Full Bill Payment (पूरा बिल चुकता)",
                    "Part Payment (आंशिक/किश्त)",
                ],
                horizontal=True,
            )

            if (
                pay_type
                == "Full Bill Payment (पूरा बिल चुकता)"
            ):

                p_amount = float(
                    selected_bill["Balance"]
                )

                st.info(
                    f"✅ Full Amount Selected: "
                    f"**Rs {p_amount:,.2f}** "
                    f"for Bill "
                    f"**{selected_bill['Bill_No']}**"
                )

            else:

                p_amount = st.number_input(
                    "Enter Part Payment Amount (Rs)",
                    min_value=0.0,
                    max_value=float(
                        selected_bill["Balance"]
                    ),
                    step=50.0,
                    key="p_amt_part",
                )

            p_mode = st.selectbox(
                "Payment Mode",
                [
                    "Cash",
                    "UPI / PhonePe / GPay",
                    "Bank Transfer",
                    "Cheque",
                ],
                key="p_mode",
            )

            if st.button(
                "🟢 Receive & Clear Payment",
                use_container_width=True,
            ):

                if p_amount <= 0:

                    st.error(
                        "Please enter a valid amount "
                        "greater than zero!"
                    )

                else:

                    formatted_date = (
                        p_date.strftime("%d-%m-%Y")
                    )

                    is_full_flag = (
                        pay_type
                        == "Full Bill Payment (पूरा बिल चुकता)"
                    )

                    success, result = record_bill_payment(
                        str(
                            selected_bill["Bill_No"]
                        ),
                        formatted_date,
                        p_outlet,
                        str(
                            selected_bill[
                                "Manager_Name"
                            ]
                        ),
                        float(p_amount),
                        p_mode,
                        is_full_flag,
                    )

                    if success:

                        st.success(
                            f"🟢 Payment of "
                            f"Rs {result:,.2f} "
                            f"recorded for Bill "
                            f"{selected_bill['Bill_No']}"
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"❌ {result}"
                        )


# ==============================================================================
# DASHBOARD
# ==============================================================================

st.markdown("---")

st.subheader(
    "📊 Business Dashboard & Records"
)

tab_bills, tab_payments = st.tabs(
    [
        "📋 All Bills Ledger (बकाया बिल लिस्ट)",
        "🧾 Payments Received History (प्राप्त पेमेंट रसीदें)",
    ]
)


# ==============================================================================
# TAB 1 - ALL BILLS
# ==============================================================================

with tab_bills:

    if bills_df.empty:

        st.info(
            "No bills recorded yet."
        )

    else:

        f_col1, f_col2 = st.columns(2)

        with f_col1:

            selected_mgr_filter = st.selectbox(
                "Filter by Manager:",
                options=[
                    "All Managers"
                ] + managers_list,
                key="filter_mgr_tab1",
            )

        if selected_mgr_filter == "All Managers":

            filtered_outlets = [
                "All Outlets"
            ] + outlets_list

        else:

            mgr_outlets = list(
                bills_df[
                    bills_df["Manager_Name"]
                    == selected_mgr_filter
                ]["Outlet_Name"].unique()
            )

            filtered_outlets = [
                "All Outlets"
            ] + sorted(mgr_outlets)

        with f_col2:

            selected_outlet_filter = st.selectbox(
                "Filter by Outlet / Customer:",
                options=filtered_outlets,
                key="filter_outlet_tab1",
            )

        df_view = bills_df.copy()

        if selected_mgr_filter != "All Managers":

            df_view = df_view[
                df_view["Manager_Name"]
                == selected_mgr_filter
            ]

        if selected_outlet_filter != "All Outlets":

            df_view = df_view[
                df_view["Outlet_Name"]
                == selected_outlet_filter
            ]

        tot_due = df_view["Balance"].sum()

        st.metric(
            "🔴 TOTAL NET DUES BALANCE",
            f"Rs {tot_due:,.2f}",
        )

        st.markdown(
            "#### 📋 Detailed Bills"
        )

        (
            h_col1,
            h_col2,
            h_col3,
            h_col4,
            h_col5,
            h_col6,
            h_col7,
            h_col8,
            h_col9,
            h_col10,
            h_col11,
        ) = st.columns(
            [
                1.0,
                0.9,
                1.2,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                0.7,
                0.7,
            ]
        )

        h_col1.write("**Bill Code**")
        h_col2.write("**Date**")
        h_col3.write("**Outlet**")
        h_col4.write("**Manager**")
        h_col5.write("**Bill Amt**")
        h_col6.write("**Paid Amt**")
        h_col7.write("**Balance**")
        h_col8.write("**Status**")
        h_col9.write("**⏰ Dues Days**")
        h_col10.write("**Edit**")
        h_col11.write("**Delete**")

        st.divider()

        for idx, row in df_view.iterrows():

            is_paid = row["Balance"] <= 0

            days_p = (
                calculate_days_pending(
                    row["Date"]
                )
                if not is_paid
                else 0
            )

            with st.container():

                (
                    c1,
                    c2,
                    c3,
                    c4,
                    c5,
                    c6,
                    c7,
                    c8,
                    c9,
                    c10,
                    c11,
                ) = st.columns(
                    [
                        1.0,
                        0.9,
                        1.2,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.7,
                        0.7,
                    ]
                )

                c1.write(
                    f"**{row['Bill_No']}**"
                )

                c2.write(
                    row["Date"]
                )

                c3.write(
                    row["Outlet_Name"]
                )

                c4.write(
                    row["Manager_Name"]
                )

                c5.write(
                    f"Rs {row['Bill_Amount']:,.2f}"
                )

                c6.write(
                    f"Rs {row['Paid_Amount']:,.2f}"
                )

                c7.write(
                    f"Rs {row['Balance']:,.2f}"
                )

                if row["Status"] == "🟢 PAID":

                    c8.markdown(
                        "**🟢 PAID**"
                    )

                elif row["Status"] == "🔴 PARTIAL":

                    c8.markdown(
                        "**🔴 PARTIAL**"
                    )

                else:

                    c8.markdown(
                        "**🔴 UNPAID**"
                    )

                if not is_paid:

                    c9.markdown(
                        f"**⏰ {days_p} Days**"
                    )

                else:

                    c9.write(
                        "0 Days"
                    )

                # ------------------------------------------------------------------
                # EDIT
                # ------------------------------------------------------------------

                if c10.button(
                    "✏️",
                    key=f"edit_b_{row['Bill_No']}",
                    help="Modify this bill",
                ):

                    st.session_state[
                        f"editing_bill_{row['Bill_No']}"
                    ] = True

                    st.rerun()

                # ------------------------------------------------------------------
                # DELETE - ADMIN ONLY
                # ------------------------------------------------------------------

                if current_role == "admin":

                    if c11.button(
                        "🗑️",
                        key=f"del_b_{row['Bill_No']}",
                        help="Delete this bill",
                    ):

                        st.session_state[
                            f"confirm_delete_bill_{row['Bill_No']}"
                        ] = True

                        st.rerun()

                else:

                    c11.write("🔒")

                # ------------------------------------------------------------------
                # EDIT FORM
                # ------------------------------------------------------------------

                if st.session_state.get(
                    f"editing_bill_{row['Bill_No']}",
                    False,
                ):

                    st.markdown(
                        f"""
                        <div class="edit-card">
                            <h4 style="color:#B7791F; margin:0;">
                                ✏️ MODIFY BILL:
                                {row['Bill_No']}
                            </h4>
                            <p style="margin:0;">
                                Existing bill details ko yahan modify karein.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:

                        edit_date = st.date_input(
                            "Bill Date",
                            datetime.strptime(
                                row["Date"],
                                "%d-%m-%Y",
                            ),
                            format="DD/MM/YYYY",
                            key=f"edit_date_{row['Bill_No']}",
                        )

                        edit_manager = st.selectbox(
                            "Sales Manager",
                            managers_list,
                            index=(
                                managers_list.index(
                                    row["Manager_Name"]
                                )
                                if row["Manager_Name"]
                                in managers_list
                                else 0
                            ),
                            key=f"edit_mgr_{row['Bill_No']}",
                        )

                    with edit_col2:

                        edit_outlet = st.text_input(
                            "Customer / Outlet Name",
                            value=row[
                                "Outlet_Name"
                            ],
                            key=f"edit_outlet_{row['Bill_No']}",
                        )

                        edit_amount = st.number_input(
                            "Bill Amount (Rs)",
                            min_value=float(
                                row["Paid_Amount"]
                            ),
                            value=float(
                                row["Bill_Amount"]
                            ),
                            step=50.0,
                            key=f"edit_amount_{row['Bill_No']}",
                        )

                    edit_note = st.text_input(
                        "Bill Details / Goods Note",
                        value=(
                            row["Note"]
                            if row["Note"]
                            else ""
                        ),
                        key=f"edit_note_{row['Bill_No']}",
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "💾 Save Changes",
                            key=f"save_edit_{row['Bill_No']}",
                            use_container_width=True,
                        ):

                            new_outlet = (
                                edit_outlet
                                .strip()
                                .title()
                            )

                            if not new_outlet:

                                st.error(
                                    "Outlet name cannot be empty."
                                )

                            elif (
                                edit_amount
                                < float(
                                    row["Paid_Amount"]
                                )
                            ):

                                st.error(
                                    f"Bill amount cannot be "
                                    f"less than paid amount "
                                    f"Rs "
                                    f"{row['Paid_Amount']:,.2f}."
                                )

                            else:

                                success, message = (
                                    update_bill_in_db(
                                        row["Bill_No"],
                                        edit_date.strftime(
                                            "%d-%m-%Y"
                                        ),
                                        edit_manager,
                                        new_outlet,
                                        float(
                                            edit_amount
                                        ),
                                        edit_note,
                                    )
                                )

                                if success:

                                    st.success(
                                        f"✅ Bill "
                                        f"{row['Bill_No']} "
                                        f"modified successfully!"
                                    )

                                    st.session_state[
                                        f"editing_bill_{row['Bill_No']}"
                                    ] = False

                                    st.rerun()

                                else:

                                    st.error(
                                        message
                                    )

                    with cancel_col:

                        if st.button(
                            "❌ Cancel",
                            key=f"cancel_edit_{row['Bill_No']}",
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"editing_bill_{row['Bill_No']}"
                            ] = False

                            st.rerun()

                # ------------------------------------------------------------------
                # DELETE CONFIRMATION - ADMIN ONLY
                # ------------------------------------------------------------------

                if (
                    current_role == "admin"
                    and st.session_state.get(
                        f"confirm_delete_bill_{row['Bill_No']}",
                        False,
                    )
                ):

                    st.markdown(
                        f"""
                        <div class="delete-card">
                            <h4 style="color:#B91C1C; margin:0;">
                                ⚠️ DELETE CONFIRMATION
                            </h4>
                            <p style="margin:5px 0 0 0;">
                                Are you sure you want to delete
                                Bill <b>{row['Bill_No']}</b>
                                for
                                <b>{row['Outlet_Name']}</b>?
                                <br>
                                Is bill ke saath associated
                                payment history bhi delete ho jayegi.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    confirm_col1, confirm_col2 = st.columns(2)

                    with confirm_col1:

                        if st.button(
                            "✅ Yes, Delete",
                            key=f"confirm_yes_{row['Bill_No']}",
                            use_container_width=True,
                        ):

                            delete_bill_from_db(
                                row["Bill_No"]
                            )

                            st.session_state[
                                f"confirm_delete_bill_{row['Bill_No']}"
                            ] = False

                            st.success(
                                f"Bill #{row['Bill_No']} "
                                f"deleted successfully!"
                            )

                            st.rerun()

                    with confirm_col2:

                        if st.button(
                            "❌ Cancel",
                            key=f"confirm_no_{row['Bill_No']}",
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"confirm_delete_bill_{row['Bill_No']}"
                            ] = False

                            st.rerun()

        # ----------------------------------------------------------------------
        # PDF EXPORT
        # ----------------------------------------------------------------------

        st.markdown("---")

        rep_sub = (
            f"Outlet: {selected_outlet_filter} | "
            f"Manager: {selected_mgr_filter}"
        )

        pdf_bytes = generate_pdf_report(
            df_view,
            subtitle_info=rep_sub,
        )

        st.download_button(
            label="📄 Download Bills PDF Statement",
            data=pdf_bytes,
            file_name=(
                f"Bill_Statement_"
                f"{selected_outlet_filter}_"
                f"{datetime.now().strftime('%d%m%Y')}.pdf"
            ),
            mime="application/pdf",
        )


# ==============================================================================
# TAB 2 - PAYMENTS HISTORY
# ==============================================================================

with tab_payments:

    st.markdown(
        "### 🟢 History of All Received Payments"
    )

    if payments_df.empty:

        st.info(
            "No payments received yet."
        )

    else:

        total_rec = (
            payments_df["Amount_Paid"].sum()
        )

        st.metric(
            "Total Payments Collected",
            f"Rs {total_rec:,.2f}",
        )

        (
            p_col1,
            p_col2,
            p_col3,
            p_col4,
            p_col5,
            p_col6,
            p_col7,
        ) = st.columns(
            [
                1.0,
                1.2,
                1.5,
                1.2,
                1.2,
                1.2,
                1.0,
            ]
        )

        p_col1.write("**Date**")
        p_col2.write("**Bill Code**")
        p_col3.write("**Outlet / Store**")
        p_col4.write("**Manager**")
        p_col5.write("**Amount Received**")
        p_col6.write("**Mode**")
        p_col7.write("**Action**")

        st.divider()

        for p_idx, p_row in payments_df.iterrows():

            with st.container():

                (
                    pc1,
                    pc2,
                    pc3,
                    pc4,
                    pc5,
                    pc6,
                    pc7,
                ) = st.columns(
                    [
                        1.0,
                        1.2,
                        1.5,
                        1.2,
                        1.2,
                        1.2,
                        1.0,
                    ]
                )

                pc1.write(
                    p_row["Date"]
                )

                pc2.write(
                    f"**{p_row['Bill_No']}**"
                )

                pc3.write(
                    p_row["Outlet_Name"]
                )

                pc4.write(
                    p_row["Manager_Name"]
                )

                pc5.markdown(
                    f"**🟢 Rs "
                    f"{p_row['Amount_Paid']:,.2f}**"
                )

                pc6.write(
                    p_row["Payment_Mode"]
                )

                # ------------------------------------------------------------------
                # PAYMENT DELETE - ADMIN ONLY
                # ------------------------------------------------------------------

                if current_role == "admin":

                    if pc7.button(
                        "🗑️",
                        key=f"del_p_{p_row['Payment_ID']}",
                        help="Delete payment entry",
                    ):

                        st.session_state[
                            f"confirm_delete_payment_{p_row['Payment_ID']}"
                        ] = True

                        st.rerun()

                else:

                    pc7.write("🔒")

                # ------------------------------------------------------------------
                # PAYMENT DELETE CONFIRMATION
                # ------------------------------------------------------------------

                if (
                    current_role == "admin"
                    and st.session_state.get(
                        f"confirm_delete_payment_{p_row['Payment_ID']}",
                        False,
                    )
                ):

                    st.markdown(
                        f"""
                        <div class="delete-card">
                            <h4 style="color:#B91C1C; margin:0;">
                                ⚠️ PAYMENT DELETE CONFIRMATION
                            </h4>
                            <p style="margin:5px 0 0 0;">
                                Delete payment of
                                <b>Rs {p_row['Amount_Paid']:,.2f}</b>
                                for Bill
                                <b>{p_row['Bill_No']}</b>?
                                <br>
                                Bill ka paid amount aur balance
                                automatically recalculate hoga.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    pay_confirm_col1, pay_confirm_col2 = (
                        st.columns(2)
                    )

                    with pay_confirm_col1:

                        if st.button(
                            "✅ Yes, Delete Payment",
                            key=(
                                f"confirm_yes_p_"
                                f"{p_row['Payment_ID']}"
                            ),
                            use_container_width=True,
                        ):

                            delete_payment_from_db(
                                p_row["Payment_ID"],
                                p_row["Bill_No"],
                            )

                            st.session_state[
                                f"confirm_delete_payment_{p_row['Payment_ID']}"
                            ] = False

                            st.success(
                                "Payment entry removed "
                                "and bill balance updated!"
                            )

                            st.rerun()

                    with pay_confirm_col2:

                        if st.button(
                            "❌ Cancel",
                            key=(
                                f"confirm_no_p_"
                                f"{p_row['Payment_ID']}"
                            ),
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"confirm_delete_payment_{p_row['Payment_ID']}"
                            ] = False

                            st.rerun()

        # ----------------------------------------------------------------------
        # WHATSAPP RECEIPT
        # ----------------------------------------------------------------------

        st.markdown("---")

        st.markdown(
            "#### 📲 Send Payment Receipt to Customer via WhatsApp"
        )

        wa_p_col1, wa_p_col2 = st.columns(2)

        with wa_p_col1:

            rec_wa_phone = st.text_input(
                "Customer Mobile No",
                placeholder="91XXXXXXXXXX",
                key="rec_wa_phone_key",
            )

        with wa_p_col2:

            latest_pay = payments_df.iloc[0]

            if st.button(
                "💬 Send Latest Payment Confirmation Receipt"
            ):

                phone = (
                    rec_wa_phone
                    .strip()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("+", "")
                )

                if (
                    phone.isdigit()
                    and 10 <= len(phone) <= 15
                ):

                    msg = (
                        "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
                    )

                    msg += (
                        "*PAYMENT RECEIPT "
                        "(भुगतान रसीद)*\n"
                    )

                    msg += (
                        "-----------------------------------\n"
                    )

                    msg += (
                        f"👤 *Store Name:* "
                        f"{latest_pay['Outlet_Name']}\n"
                    )

                    msg += (
                        f"🧾 *Bill Code:* "
                        f"{latest_pay['Bill_No']}\n"
                    )

                    msg += (
                        f"📅 *Payment Date:* "
                        f"{latest_pay['Date']}\n"
                    )

                    msg += (
                        f"🟢 *AMOUNT RECEIVED:* "
                        f"Rs "
                        f"{latest_pay['Amount_Paid']:,.2f}\n"
                    )

                    msg += (
                        f"💳 *Payment Mode:* "
                        f"{latest_pay['Payment_Mode']}\n"
                    )

                    msg += (
                        "-----------------------------------\n"
                    )

                    msg += (
                        "Thank you for your payment! "
                        "(धन्यवाद!)\n"
                    )

                    encoded_msg = (
                        urllib.parse.quote(msg)
                    )

                    wa_link = (
                        "https://api.whatsapp.com/send"
                        "?phone="
                        f"{phone}"
                        f"&text={encoded_msg}"
                    )

                    st.markdown(
                        f"[👉 Click Here to Send Payment "
                        f"Receipt on WhatsApp]({wa_link})"
                    )

                else:

                    st.warning(
                        "Please enter a valid mobile number "
                        "with country code."
                    )
