import io
import sqlite3
import urllib.parse
from datetime import datetime, date

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

    .blue-card {
        background-color: #EFF6FF;
        border-left: 6px solid #2563EB;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .orange-card {
        background-color: #FFF7ED;
        border-left: 6px solid #F97316;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .outlet-heading {
        font-size: 24px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 2px;
    }

    .small-muted {
        color: #64748B;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥤 MS MAA VINDHYAWASINI TRADERS (COCA COLA)")
st.caption(
    "Bill-Wise Ledger System - Auto Generated Bill Code (NAME + SERIAL NO)"
)


# ==============================================================================
# DATABASE
# ==============================================================================

DB_FILE = "khatabook_billwise_v6.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


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
        "INSERT OR IGNORE INTO managers (name) VALUES ('Default Manager')"
    )

    conn.commit()
    conn.close()


def get_all_bills():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM bills ORDER BY Bill_ID DESC",
        conn,
    )

    conn.close()
    return df


def get_all_payments():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM payments ORDER BY Payment_ID DESC",
        conn,
    )

    conn.close()
    return df


def get_managers():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT name FROM managers ORDER BY name ASC",
        conn,
    )

    conn.close()

    if df.empty:
        return ["Default Manager"]

    return df["name"].tolist()


def get_outlets():
    conn = get_connection()

    c = conn.cursor()

    c.execute(
        """
        SELECT DISTINCT Outlet_Name
        FROM bills
        WHERE Outlet_Name IS NOT NULL
        AND TRIM(Outlet_Name) != ''
        ORDER BY Outlet_Name ASC
        """
    )

    outlets = [row[0] for row in c.fetchall()]

    conn.close()

    return outlets


# ==============================================================================
# BILL CODE GENERATOR
# ==============================================================================

def generate_auto_code_backend(outlet_name):

    clean_name = (
        "".join(e for e in outlet_name if e.isalnum()).upper()
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

    bill_no = generate_auto_code_backend(outlet)

    conn = get_connection()
    c = conn.cursor()

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
        VALUES (?, ?, ?, ?, ?, 0.0, ?, '🔴 UNPAID', ?)
        """,
        (
            bill_no,
            date_str,
            mgr,
            outlet,
            amount,
            amount,
            note,
        ),
    )

    conn.commit()
    conn.close()

    return bill_no


# ==============================================================================
# MODIFY EXISTING BILL
# ==============================================================================

def update_bill_in_db(
    bill_no,
    date_str,
    mgr,
    outlet,
    bill_amount,
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

    paid_amount = float(row[0] or 0)

    if bill_amount < paid_amount:
        conn.close()
        return (
            False,
            f"Bill amount cannot be less than already received amount "
            f"Rs {paid_amount:,.2f}.",
        )

    balance = float(bill_amount) - paid_amount

    if balance <= 0:
        balance = 0.0
        status = "🟢 PAID"
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
            bill_amount,
            balance,
            status,
            note,
            bill_no,
        ),
    )

    # Existing payment records ko bhi updated outlet/manager ke saath sync karein
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
# PAYMENT RECORD
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

    c.execute(
        """
        SELECT Bill_Amount, Paid_Amount, Balance
        FROM bills
        WHERE Bill_No = ?
        """,
        (bill_no,),
    )

    row = c.fetchone()

    if row:

        bill_amt, curr_paid, curr_bal = row

        if is_full:
            actual_payment = float(curr_bal)
        else:
            actual_payment = min(
                float(paid_amt),
                float(curr_bal),
            )

        new_paid = float(curr_paid) + actual_payment
        new_bal = float(bill_amt) - new_paid

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

    conn.close()


# ==============================================================================
# DELETE BILL
# ==============================================================================

def delete_bill_from_db(bill_no):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM bills WHERE Bill_No = ?",
        (bill_no,),
    )

    c.execute(
        "DELETE FROM payments WHERE Bill_No = ?",
        (bill_no,),
    )

    conn.commit()
    conn.close()


# ==============================================================================
# DELETE PAYMENT
# ==============================================================================

def delete_payment_from_db(
    pay_id,
    bill_no,
    amt,
):

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM payments WHERE Payment_ID = ?",
        (pay_id,),
    )

    c.execute(
        """
        SELECT Bill_Amount, Paid_Amount
        FROM bills
        WHERE Bill_No = ?
        """,
        (bill_no,),
    )

    row = c.fetchone()

    if row:

        bill_amount, paid_amount = row

        new_paid = max(
            0.0,
            float(paid_amount) - float(amt),
        )

        new_balance = float(bill_amount) - new_paid

        if new_balance <= 0:
            status = "🟢 PAID"
            new_balance = 0.0
        elif new_paid > 0:
            status = "🔴 PARTIAL"
        else:
            status = "🔴 UNPAID"

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
                new_balance,
                status,
                bill_no,
            ),
        )

    conn.commit()
    conn.close()


# ==============================================================================
# MANAGER
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
# DATE / DAYS
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


def date_from_string(date_str):

    try:
        return datetime.strptime(
            date_str,
            "%d-%m-%Y",
        ).date()

    except Exception:
        return None


# ==============================================================================
# PDF REPORT GENERATOR
# ==============================================================================

def generate_pdf_report(
    df_data,
    subtitle_info="",
    report_title="BILL STATEMENT",
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

    outlet_style = ParagraphStyle(
        "OutletTitle",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#B91C1C"),
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )

    sub_title_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#B91C1C"),
        fontName="Helvetica-Bold",
        spaceAfter=6,
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
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#334155"),
    )

    red_cell_style = ParagraphStyle(
        "RedCell",
        parent=table_cell_style,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold",
    )

    green_cell_style = ParagraphStyle(
        "GreenCell",
        parent=table_cell_style,
        textColor=colors.HexColor("#16A34A"),
        fontName="Helvetica-Bold",
    )

    orange_cell_style = ParagraphStyle(
        "OrangeCell",
        parent=table_cell_style,
        textColor=colors.HexColor("#EA580C"),
        fontName="Helvetica-Bold",
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

    # Outlet heading
    outlet_names = []

    if not df_data.empty and "Outlet_Name" in df_data.columns:
        outlet_names = (
            df_data["Outlet_Name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    if len(outlet_names) == 1:
        elements.append(
            Paragraph(
                f"OUTLET: {outlet_names[0]}",
                outlet_style,
            )
        )

    elements.append(
        Paragraph(
            f"<b>Report:</b> {report_title}<br/>"
            f"<b>Statement Info:</b> {subtitle_info}<br/>"
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
        "Outlet / Customer",
        "Bill Amt (Rs)",
        "Paid Amt (Rs)",
        "Balance (Rs)",
        "Status",
    ]

    table_data = [
        [
            Paragraph(h, table_hdr_style)
            for h in headers
        ]
    ]

    for _, row in df_data.iterrows():

        status_value = str(row["Status"])

        if "PAID" in status_value and "PARTIAL" not in status_value:

            status_style = green_cell_style
            status_text = "PAID"

        elif "PARTIAL" in status_value:

            status_style = orange_cell_style
            status_text = "PARTIAL"

        else:

            status_style = red_cell_style
            status_text = "UNPAID"

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
                    green_cell_style
                    if float(row["Paid_Amount"]) > 0
                    else table_cell_style,
                ),

                Paragraph(
                    f"Rs {row['Balance']:,.2f}",
                    red_cell_style
                    if float(row["Balance"]) > 0
                    else green_cell_style,
                ),

                Paragraph(
                    status_text,
                    status_style,
                ),
            ]
        )

    if df_data.empty:

        table_data.append(
            [
                Paragraph(
                    "No records found",
                    table_cell_style,
                )
            ]
            + [
                ""
                for _ in range(6)
            ]
        )

    t = Table(
        table_data,
        colWidths=[
            62,
            55,
            125,
            67,
            67,
            67,
            65,
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
                    4,
                ),
            ]
        )
    )

    elements.append(t)

    # --------------------------------------------------------------------------
    # TOTAL NET DUES
    # --------------------------------------------------------------------------

    total_bill = (
        float(df_data["Bill_Amount"].sum())
        if not df_data.empty
        else 0.0
    )

    total_paid = (
        float(df_data["Paid_Amount"].sum())
        if not df_data.empty
        else 0.0
    )

    total_due = (
        float(df_data["Balance"].sum())
        if not df_data.empty
        else 0.0
    )

    elements.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#CBD5E1"),
            spaceBefore=12,
            spaceAfter=8,
        )
    )

    summary_data = [
        [
            Paragraph(
                "<b>TOTAL BILLED</b>",
                table_cell_style,
            ),
            Paragraph(
                "<b>TOTAL PAID</b>",
                table_cell_style,
            ),
            Paragraph(
                "<b>TOTAL NET DUES</b>",
                red_cell_style
                if total_due > 0
                else green_cell_style,
            ),
        ],
        [
            Paragraph(
                f"Rs {total_bill:,.2f}",
                table_cell_style,
            ),
            Paragraph(
                f"Rs {total_paid:,.2f}",
                green_cell_style,
            ),
            Paragraph(
                f"Rs {total_due:,.2f}",
                red_cell_style
                if total_due > 0
                else green_cell_style,
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[180, 180, 180],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "BACKGROUND",
                    (2, 1),
                    (2, 1),
                    colors.HexColor("#FEF2F2")
                    if total_due > 0
                    else colors.HexColor("#F0FDF4"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    elements.append(summary_table)

    doc.build(elements)

    buffer.seek(0)

    return buffer.getvalue()


# ==============================================================================
# PAYMENT RECEIPT PDF
# ==============================================================================

def generate_payment_receipt_pdf(payment_row):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        alignment=1,
        spaceAfter=5,
    )

    green_style = ParagraphStyle(
        "ReceiptGreen",
        parent=styles["Normal"],
        fontSize=16,
        textColor=colors.HexColor("#16A34A"),
        fontName="Helvetica-Bold",
        alignment=1,
        spaceAfter=15,
    )

    normal_style = ParagraphStyle(
        "ReceiptNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#334155"),
    )

    elements = []

    elements.append(
        Paragraph(
            "🥤 MS MAA VINDHYAWASINI TRADERS",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "PAYMENT RECEIPT",
            green_style,
        )
    )

    receipt_data = [
        ["Store / Outlet", str(payment_row["Outlet_Name"])],
        ["Bill Code", str(payment_row["Bill_No"])],
        ["Payment Date", str(payment_row["Date"])],
        ["Amount Received", f"Rs {payment_row['Amount_Paid']:,.2f}"],
        ["Payment Mode", str(payment_row["Payment_Mode"])],
        ["Sales Manager", str(payment_row["Manager_Name"])],
    ]

    table = Table(
        [
            [
                Paragraph(f"<b>{a}</b>", normal_style),
                Paragraph(str(b), normal_style),
            ]
            for a, b in receipt_data
        ],
        colWidths=[160, 300],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    elements.append(table)

    elements.append(
        Paragraph(
            "<br/><br/><b>Thank you for your payment!</b><br/>"
            "धन्यवाद!",
            normal_style,
        )
    )

    doc.build(elements)

    buffer.seek(0)

    return buffer.getvalue()


# ==============================================================================
# WHATSAPP LINK
# ==============================================================================

def create_whatsapp_link(phone, message):

    clean_phone = (
        str(phone)
        .strip()
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
    )

    encoded_message = urllib.parse.quote(message)

    return (
        "https://api.whatsapp.com/send?"
        f"phone={clean_phone}"
        f"&text={encoded_message}"
    )


# ==============================================================================
# INITIALIZE
# ==============================================================================

init_db()

managers_list = get_managers()
outlets_list = get_outlets()
bills_df = get_all_bills()
payments_df = get_all_payments()


# ==============================================================================
# SESSION STATE
# ==============================================================================

if "confirm_delete_bill" not in st.session_state:
    st.session_state.confirm_delete_bill = None

if "confirm_delete_payment" not in st.session_state:
    st.session_state.confirm_delete_payment = None


# ==============================================================================
# SIDEBAR
# ==============================================================================

with st.sidebar:

    st.header("⚙️ Master Settings")

    with st.expander("👤 Manager Setup"):

        new_mgr = st.text_input(
            "Add New Sales Manager",
            key="new_manager_input",
        )

        if st.button(
            "Save Manager",
            use_container_width=True,
        ):

            if new_mgr.strip():

                save_manager_to_db(new_mgr)

                st.success(
                    f"Added Manager: {new_mgr}"
                )

                st.rerun()

        st.divider()

        st.write("**Current Managers:**")

        st.write(
            ", ".join(managers_list)
        )

    with st.expander("💾 Backup CSV"):

        if not bills_df.empty:

            csv_buf = bills_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                label="📥 Download Bills CSV Backup",
                data=csv_buf,
                file_name=(
                    "maa_vindhyawasini_bills_"
                    f"{datetime.now().strftime('%d-%m-%Y')}.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )

    with st.expander("💳 Payment CSV Backup"):

        if not payments_df.empty:

            payment_csv = payments_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                label="📥 Download Payments CSV",
                data=payment_csv,
                file_name=(
                    "maa_vindhyawasini_payments_"
                    f"{datetime.now().strftime('%d-%m-%Y')}.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )


# ==============================================================================
# NEW BILL / PAYMENT ENTRY
# ==============================================================================

st.markdown("---")

col_left, col_right = st.columns(2)


# ==============================================================================
# NEW BILL
# ==============================================================================

with col_left:

    st.markdown(
        """
        <div class="red-card">
            <h3 style="color:#C9302C;margin:0;">
                🔴 CREATE NEW BILL / DUES
            </h3>
            <p style="margin:0;font-size:13px;color:#555;">
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

    existing_outlets = (
        ["+ Add New Customer/Outlet"]
        + outlets_list
    )

    selected_b_outlet = st.selectbox(
        "Customer / Outlet Name",
        existing_outlets,
        key="b_outlet_select",
    )

    if selected_b_outlet == "+ Add New Customer/Outlet":

        b_outlet = st.text_input(
            "Enter Store Name (दुकान का नाम)",
            placeholder="e.g. RAM TRADERS",
            key="b_outlet_text",
        )

    else:

        b_outlet = selected_b_outlet

    st.info(
        "💡 Bill Code जैसे RAM-1, RAHUL-2 "
        "ऑटोमैटिक जेनरेट होगा।"
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
                b_outlet.strip().title()
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
            <h3 style="color:#4CAE4C;margin:0;">
                🟢 BILL-WISE PAYMENT RECEIVED
            </h3>
            <p style="margin:0;font-size:13px;color:#555;">
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
                f"🎉 No outstanding unpaid bills for {p_outlet}!"
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
                    f"for Bill **{selected_bill['Bill_No']}**"
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
                        "Please enter a valid amount greater than zero!"
                    )

                else:

                    formatted_date = (
                        p_date.strftime("%d-%m-%Y")
                    )

                    is_full_flag = (
                        pay_type
                        == "Full Bill Payment (पूरा बिल चुकता)"
                    )

                    record_bill_payment(
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

                    st.success(
                        f"🟢 Payment of "
                        f"Rs {p_amount:,.2f} "
                        f"recorded for Bill "
                        f"{selected_bill['Bill_No']}"
                    )

                    st.rerun()


# ==============================================================================
# DASHBOARD
# ==============================================================================

st.markdown("---")

st.subheader(
    "📊 Business Dashboard & Records"
)

tab_bills, tab_payments = st.tabs(
    [
        "📋 All Bills Ledger",
        "🧾 Payments Received History",
    ]
)


# ==============================================================================
# TAB 1 - BILLS
# ==============================================================================

with tab_bills:

    if bills_df.empty:

        st.info(
            "No bills recorded yet."
        )

    else:

        # ----------------------------------------------------------------------
        # SEARCH BOX
        # ----------------------------------------------------------------------

        st.markdown(
            """
            <div class="blue-card">
                <h3 style="color:#1D4ED8;margin:0;">
                    🔍 Search & Filter Bills
                </h3>
                <p class="small-muted">
                    Search by Bill Code, Outlet, Manager or Bill Details
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        search_text = st.text_input(
            "🔍 Search",
            placeholder=(
                "Bill Code / Outlet / Manager / "
                "Bill Details..."
            ),
            key="bill_search_box",
        )

        # ----------------------------------------------------------------------
        # MANAGER FILTER
        # ----------------------------------------------------------------------

        f_col1, f_col2 = st.columns(2)

        with f_col1:

            selected_mgr_filter = st.selectbox(
                "Filter by Manager:",
                options=[
                    "All Managers"
                ]
                + managers_list,
                key="filter_mgr_tab1",
            )

        if selected_mgr_filter == "All Managers":

            filtered_outlets = (
                ["All Outlets"]
                + outlets_list
            )

        else:

            mgr_outlets = list(
                bills_df[
                    bills_df["Manager_Name"]
                    == selected_mgr_filter
                ]["Outlet_Name"]
                .unique()
            )

            filtered_outlets = (
                ["All Outlets"]
                + sorted(mgr_outlets)
            )

        with f_col2:

            selected_outlet_filter = st.selectbox(
                "Filter by Outlet / Customer:",
                options=filtered_outlets,
                key="filter_outlet_tab1",
            )

        # ----------------------------------------------------------------------
        # DATE FILTER
        # ----------------------------------------------------------------------

        st.markdown("#### 📅 Date-Wise Report")

        date_col1, date_col2 = st.columns(2)

        with date_col1:

            from_date = st.date_input(
                "From Date",
                value=date(
                    datetime.now().year,
                    1,
                    1,
                ),
                format="DD/MM/YYYY",
                key="report_from_date",
            )

        with date_col2:

            to_date = st.date_input(
                "To Date",
                value=datetime.now().date(),
                format="DD/MM/YYYY",
                key="report_to_date",
            )

        if from_date > to_date:

            st.error(
                "From Date cannot be greater than To Date."
            )

            df_view = bills_df.iloc[0:0].copy()

        else:

            df_view = bills_df.copy()

            # --------------------------------------------------------------
            # SEARCH
            # --------------------------------------------------------------

            if search_text.strip():

                search_lower = (
                    search_text.strip().lower()
                )

                search_mask = (
                    df_view["Bill_No"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        search_lower,
                        na=False,
                    )
                    |
                    df_view["Outlet_Name"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        search_lower,
                        na=False,
                    )
                    |
                    df_view["Manager_Name"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        search_lower,
                        na=False,
                    )
                    |
                    df_view["Note"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        search_lower,
                        na=False,
                    )
                )

                df_view = df_view[
                    search_mask
                ]

            # --------------------------------------------------------------
            # MANAGER
            # --------------------------------------------------------------

            if (
                selected_mgr_filter
                != "All Managers"
            ):

                df_view = df_view[
                    df_view["Manager_Name"]
                    == selected_mgr_filter
                ]

            # --------------------------------------------------------------
            # OUTLET
            # --------------------------------------------------------------

            if (
                selected_outlet_filter
                != "All Outlets"
            ):

                df_view = df_view[
                    df_view["Outlet_Name"]
                    == selected_outlet_filter
                ]

            # --------------------------------------------------------------
            # DATE RANGE
            # --------------------------------------------------------------

            df_view["_Report_Date"] = (
                df_view["Date"]
                .apply(date_from_string)
            )

            df_view = df_view[
                (
                    df_view["_Report_Date"]
                    >= from_date
                )
                &
                (
                    df_view["_Report_Date"]
                    <= to_date
                )
            ]

            df_view = df_view.drop(
                columns=["_Report_Date"],
                errors="ignore",
            )

        # ----------------------------------------------------------------------
        # DASHBOARD - ONLY TOTAL NET DUES
        # ----------------------------------------------------------------------

        tot_due = (
            float(df_view["Balance"].sum())
            if not df_view.empty
            else 0.0
        )

        st.markdown("### 💰 Total Net Dues")

        st.metric(
            "🔴 TOTAL NET DUES",
            f"Rs {tot_due:,.2f}",
        )

        # ----------------------------------------------------------------------
        # BILL-WISE WHATSAPP
        # ----------------------------------------------------------------------

        st.markdown("---")

        st.markdown(
            """
            <div class="green-card">
                <h3 style="color:#15803D;margin:0;">
                    📲 WhatsApp Bill
                </h3>
                <p class="small-muted">
                    Select a bill, download its PDF and open WhatsApp
                    with bill details automatically prepared.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not df_view.empty:

            wa_bill_options = {}

            for _, wa_row in df_view.iterrows():

                wa_label = (
                    f"{wa_row['Bill_No']} | "
                    f"{wa_row['Outlet_Name']} | "
                    f"Rs {wa_row['Bill_Amount']:,.2f}"
                )

                wa_bill_options[
                    wa_label
                ] = wa_row

            wa_col1, wa_col2 = st.columns(2)

            with wa_col1:

                selected_wa_label = st.selectbox(
                    "Select Bill for WhatsApp:",
                    list(
                        wa_bill_options.keys()
                    ),
                    key="whatsapp_bill_select",
                )

                selected_wa_bill = (
                    wa_bill_options[
                        selected_wa_label
                    ]
                )

            with wa_col2:

                wa_phone = st.text_input(
                    "Customer WhatsApp Number",
                    placeholder="91XXXXXXXXXX",
                    key="whatsapp_bill_phone",
                )

            wa_pdf_bytes = generate_pdf_report(
                pd.DataFrame(
                    [selected_wa_bill]
                ),
                subtitle_info=(
                    f"Bill: "
                    f"{selected_wa_bill['Bill_No']}"
                ),
                report_title="INDIVIDUAL BILL",
            )

            wa_file_name = (
                f"Bill_{selected_wa_bill['Bill_No']}.pdf"
            )

            st.download_button(
                "📄 Download Selected Bill PDF",
                data=wa_pdf_bytes,
                file_name=wa_file_name,
                mime="application/pdf",
                use_container_width=True,
                key="download_selected_bill_pdf",
            )

            wa_message = (
                "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
                "*BILL / PAYMENT STATEMENT*\n"
                "-----------------------------------\n"
                f"👤 *Store Name:* "
                f"{selected_wa_bill['Outlet_Name']}\n"
                f"🧾 *Bill Code:* "
                f"{selected_wa_bill['Bill_No']}\n"
                f"📅 *Bill Date:* "
                f"{selected_wa_bill['Date']}\n"
                f"💰 *Bill Amount:* "
                f"Rs {selected_wa_bill['Bill_Amount']:,.2f}\n"
                f"🟢 *Paid Amount:* "
                f"Rs {selected_wa_bill['Paid_Amount']:,.2f}\n"
                f"🔴 *Net Balance:* "
                f"Rs {selected_wa_bill['Balance']:,.2f}\n"
                f"📌 *Status:* "
                f"{selected_wa_bill['Status']}\n"
                "-----------------------------------\n"
                "Thank you!\n"
                "MS MAA VINDHYAWASINI TRADERS"
            )

            if wa_phone.strip():

                wa_link = create_whatsapp_link(
                    wa_phone,
                    wa_message,
                )

                st.markdown(
                    f"""
                    <a href="{wa_link}"
                    target="_blank"
                    style="
                    display:inline-block;
                    padding:12px 18px;
                    background:#25D366;
                    color:white;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:bold;
                    ">
                    💬 Open WhatsApp & Send Bill Details
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(
                    "📌 PDF पहले ऊपर से download करें, "
                    "फिर WhatsApp में attachment के रूप में "
                    "PDF select करके भेज सकते हैं."
                )

            else:

                st.info(
                    "WhatsApp number enter करें."
                )

        # ----------------------------------------------------------------------
        # DETAILED BILLS
        # ----------------------------------------------------------------------

        st.markdown("---")

        st.markdown(
            "#### 📋 Detailed Bills"
        )

        if df_view.empty:

            st.warning(
                "Selected search/filter/date range में "
                "कोई bill नहीं मिला."
            )

        else:

            # ------------------------------------------------------------------
            # HEADER
            # Dues Days SECOND LAST
            # ------------------------------------------------------------------

            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7, h_col8, h_col9, h_col10 = (
                st.columns(
                    [
                        1.1,
                        1.0,
                        1.3,
                        1.1,
                        1.1,
                        1.1,
                        1.1,
                        1.1,
                        1.0,
                        0.7,
                    ]
                )
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
            h_col10.write("**Action**")

            st.divider()

            # ------------------------------------------------------------------
            # ROWS
            # ------------------------------------------------------------------

            for idx, row in df_view.iterrows():

                is_paid = (
                    float(row["Balance"])
                    <= 0
                )

                days_p = (
                    calculate_days_pending(
                        row["Date"]
                    )
                    if not is_paid
                    else 0
                )

                with st.container():

                    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = (
                        st.columns(
                            [
                                1.1,
                                1.0,
                                1.3,
                                1.1,
                                1.1,
                                1.1,
                                1.1,
                                1.1,
                                1.0,
                                0.7,
                            ]
                        )
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

                    # ----------------------------------------------------------
                    # ACTION BUTTON
                    # ----------------------------------------------------------

                    if c10.button(
                        "⚙️",
                        key=f"action_bill_{row['Bill_No']}",
                        help="Edit / Delete Bill",
                    ):

                        st.session_state[
                            "selected_action_bill"
                        ] = row["Bill_No"]

                        st.rerun()

                # ----------------------------------------------------------------
                # ACTION PANEL
                # ----------------------------------------------------------------

                if (
                    st.session_state.get(
                        "selected_action_bill"
                    )
                    == row["Bill_No"]
                ):

                    with st.expander(
                        f"⚙️ Actions: {row['Bill_No']}",
                        expanded=True,
                    ):

                        act_col1, act_col2 = st.columns(
                            2
                        )

                        with act_col1:

                            st.markdown(
                                "### ✏️ Modify Existing Bill"
                            )

                            edit_date = st.date_input(
                                "Bill Date",
                                value=(
                                    date_from_string(
                                        row["Date"]
                                    )
                                    or datetime.now().date()
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
                                    if row[
                                        "Manager_Name"
                                    ]
                                    in managers_list
                                    else 0
                                ),
                                key=f"edit_mgr_{row['Bill_No']}",
                            )

                            edit_outlet = st.text_input(
                                "Outlet / Customer",
                                value=str(
                                    row["Outlet_Name"]
                                ),
                                key=f"edit_outlet_{row['Bill_No']}",
                            )

                            edit_amount = st.number_input(
                                "Bill Amount (Rs)",
                                min_value=0.0,
                                value=float(
                                    row["Bill_Amount"]
                                ),
                                step=50.0,
                                key=f"edit_amt_{row['Bill_No']}",
                            )

                            edit_note = st.text_input(
                                "Bill Details / Note",
                                value=str(
                                    row["Note"]
                                    if pd.notna(
                                        row["Note"]
                                    )
                                    else ""
                                ),
                                key=f"edit_note_{row['Bill_No']}",
                            )

                            save_edit_col1, save_edit_col2 = (
                                st.columns(2)
                            )

                            with save_edit_col1:

                                if st.button(
                                    "💾 Update Bill",
                                    use_container_width=True,
                                    key=f"save_edit_{row['Bill_No']}",
                                ):

                                    if not edit_outlet.strip():

                                        st.error(
                                            "Outlet name required."
                                        )

                                    elif edit_amount <= 0:

                                        st.error(
                                            "Bill amount must be greater than zero."
                                        )

                                    else:

                                        ok, message = (
                                            update_bill_in_db(
                                                row["Bill_No"],
                                                edit_date.strftime(
                                                    "%d-%m-%Y"
                                                ),
                                                edit_manager,
                                                edit_outlet.strip().title(),
                                                float(edit_amount),
                                                edit_note,
                                            )
                                        )

                                        if ok:

                                            st.success(
                                                message
                                            )

                                            st.session_state[
                                                "selected_action_bill"
                                            ] = None

                                            st.rerun()

                                        else:

                                            st.error(
                                                message
                                            )

                            with save_edit_col2:

                                if st.button(
                                    "❌ Close",
                                    use_container_width=True,
                                    key=f"close_edit_{row['Bill_No']}",
                                ):

                                    st.session_state[
                                        "selected_action_bill"
                                    ] = None

                                    st.rerun()

                        with act_col2:

                            st.markdown(
                                "### 🗑️ Delete Bill"
                            )

                            st.warning(
                                f"Bill **{row['Bill_No']}** "
                                f"delete करने पर उसके साथ "
                                f"सभी payment entries भी delete हो जाएंगी."
                            )

                            if (
                                st.session_state.confirm_delete_bill
                                != row["Bill_No"]
                            ):

                                if st.button(
                                    "🗑️ Delete Bill",
                                    type="secondary",
                                    use_container_width=True,
                                    key=f"delete_bill_{row['Bill_No']}",
                                ):

                                    st.session_state[
                                        "confirm_delete_bill"
                                    ] = row["Bill_No"]

                                    st.rerun()

                            else:

                                st.error(
                                    "⚠️ क्या आप सच में इस Bill को delete करना चाहते हैं?"
                                )

                                yes_col, no_col = st.columns(
                                    2
                                )

                                with yes_col:

                                    if st.button(
                                        "✅ YES, DELETE",
                                        type="primary",
                                        use_container_width=True,
                                        key=f"yes_delete_{row['Bill_No']}",
                                    ):

                                        delete_bill_from_db(
                                            row["Bill_No"]
                                        )

                                        st.session_state[
                                            "confirm_delete_bill"
                                        ] = None

                                        st.session_state[
                                            "selected_action_bill"
                                        ] = None

                                        st.success(
                                            f"Bill {row['Bill_No']} deleted."
                                        )

                                        st.rerun()

                                with no_col:

                                    if st.button(
                                        "❌ NO, CANCEL",
                                        use_container_width=True,
                                        key=f"no_delete_{row['Bill_No']}",
                                    ):

                                        st.session_state[
                                            "confirm_delete_bill"
                                        ] = None

                                        st.rerun()

        # ----------------------------------------------------------------------
        # PDF REPORT
        # ----------------------------------------------------------------------

        st.markdown("---")

        report_info = (
            f"Date: {from_date.strftime('%d-%m-%Y')} "
            f"to {to_date.strftime('%d-%m-%Y')} | "
            f"Outlet: {selected_outlet_filter} | "
            f"Manager: {selected_mgr_filter}"
        )

        pdf_bytes = generate_pdf_report(
            df_view,
            subtitle_info=report_info,
            report_title="DATE-WISE BILL STATEMENT",
        )

        pdf_file_name = (
            "Bill_Statement_"
            f"{from_date.strftime('%d%m%Y')}_"
            f"to_"
            f"{to_date.strftime('%d%m%Y')}.pdf"
        )

        st.download_button(
            label="📄 Download Bills PDF Statement",
            data=pdf_bytes,
            file_name=pdf_file_name,
            mime="application/pdf",
            use_container_width=True,
        )


# ==============================================================================
# TAB 2 - PAYMENTS
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

        # ----------------------------------------------------------------------
        # PAYMENT SEARCH
        # ----------------------------------------------------------------------

        payment_search = st.text_input(
            "🔍 Search Payment",
            placeholder=(
                "Bill Code / Outlet / Manager / Payment Mode..."
            ),
            key="payment_search",
        )

        payment_view = payments_df.copy()

        if payment_search.strip():

            ps = (
                payment_search
                .strip()
                .lower()
            )

            mask = (
                payment_view["Bill_No"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    ps,
                    na=False,
                )
                |
                payment_view["Outlet_Name"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    ps,
                    na=False,
                )
                |
                payment_view["Manager_Name"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    ps,
                    na=False,
                )
                |
                payment_view["Payment_Mode"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    ps,
                    na=False,
                )
            )

            payment_view = payment_view[
                mask
            ]

        total_rec = (
            float(
                payment_view[
                    "Amount_Paid"
                ].sum()
            )
            if not payment_view.empty
            else 0.0
        )

        st.metric(
            "Total Payments Collected",
            f"Rs {total_rec:,.2f}",
        )

        # ----------------------------------------------------------------------
        # PAYMENT TABLE
        # ----------------------------------------------------------------------

        p_col1, p_col2, p_col3, p_col4, p_col5, p_col6, p_col7 = (
            st.columns(
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
        )

        p_col1.write("**Date**")
        p_col2.write("**Bill Code**")
        p_col3.write("**Outlet / Store**")
        p_col4.write("**Manager**")
        p_col5.write("**Amount Received**")
        p_col6.write("**Mode**")
        p_col7.write("**Action**")

        st.divider()

        for p_idx, p_row in payment_view.iterrows():

            with st.container():

                pc1, pc2, pc3, pc4, pc5, pc6, pc7 = (
                    st.columns(
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

                if pc7.button(
                    "🗑️",
                    key=f"del_p_{p_row['Payment_ID']}",
                ):

                    st.session_state[
                        "confirm_delete_payment"
                    ] = int(
                        p_row["Payment_ID"]
                    )

                    st.rerun()

            # ------------------------------------------------------------------
            # PAYMENT DELETE CONFIRMATION
            # ------------------------------------------------------------------

            if (
                st.session_state.confirm_delete_payment
                == int(p_row["Payment_ID"])
            ):

                st.error(
                    f"⚠️ Payment "
                    f"Rs {p_row['Amount_Paid']:,.2f} "
                    f"delete करना चाहते हैं?"
                )

                py_col, pn_col = st.columns(2)

                with py_col:

                    if st.button(
                        "✅ YES, DELETE PAYMENT",
                        type="primary",
                        use_container_width=True,
                        key=f"yes_del_payment_{p_row['Payment_ID']}",
                    ):

                        delete_payment_from_db(
                            p_row["Payment_ID"],
                            p_row["Bill_No"],
                            p_row["Amount_Paid"],
                        )

                        st.session_state[
                            "confirm_delete_payment"
                        ] = None

                        st.success(
                            "Payment entry removed!"
                        )

                        st.rerun()

                with pn_col:

                    if st.button(
                        "❌ NO, CANCEL",
                        use_container_width=True,
                        key=f"no_del_payment_{p_row['Payment_ID']}",
                    ):

                        st.session_state[
                            "confirm_delete_payment"
                        ] = None

                        st.rerun()

        # ----------------------------------------------------------------------
        # PAYMENT RECEIPT WHATSAPP
        # ----------------------------------------------------------------------

        st.markdown("---")

        st.markdown(
            """
            <div class="green-card">
                <h3 style="color:#15803D;margin:0;">
                    📲 Send Payment Receipt on WhatsApp
                </h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not payment_view.empty:

            latest_pay = payment_view.iloc[0]

            receipt_phone = st.text_input(
                "Customer Mobile No",
                placeholder="91XXXXXXXXXX",
                key="receipt_wa_phone",
            )

            receipt_pdf = generate_payment_receipt_pdf(
                latest_pay
            )

            st.download_button(
                "📄 Download Payment Receipt PDF",
                data=receipt_pdf,
                file_name=(
                    f"Payment_Receipt_"
                    f"{latest_pay['Bill_No']}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )

            if receipt_phone.strip():

                receipt_msg = (
                    "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
                    "*PAYMENT RECEIPT (भुगतान रसीद)*\n"
                    "-----------------------------------\n"
                    f"👤 *Store Name:* "
                    f"{latest_pay['Outlet_Name']}\n"
                    f"🧾 *Bill Code:* "
                    f"{latest_pay['Bill_No']}\n"
                    f"📅 *Payment Date:* "
                    f"{latest_pay['Date']}\n"
                    f"🟢 *AMOUNT RECEIVED:* "
                    f"Rs {latest_pay['Amount_Paid']:,.2f}\n"
                    f"💳 *Payment Mode:* "
                    f"{latest_pay['Payment_Mode']}\n"
                    "-----------------------------------\n"
                    "Thank you for your payment! (धन्यवाद!)"
                )

                receipt_wa_link = (
                    create_whatsapp_link(
                        receipt_phone,
                        receipt_msg,
                    )
                )

                st.markdown(
                    f"""
                    <a href="{receipt_wa_link}"
                    target="_blank"
                    style="
                    display:inline-block;
                    padding:12px 18px;
                    background:#25D366;
                    color:white;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:bold;
                    ">
                    💬 Open WhatsApp & Send Receipt
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(
                    "Payment Receipt PDF ऊपर से download करके "
                    "WhatsApp में attachment के रूप में भेजें."
                )

            else:

                st.warning(
                    "Please enter a valid phone number!"
                )


# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")

st.caption(
    "🥤 MS MAA VINDHYAWASINI TRADERS | "
    "Bill-Wise Ledger System"
)
