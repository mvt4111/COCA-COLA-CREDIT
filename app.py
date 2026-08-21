import io
import sqlite3
import urllib.parse
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


# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
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

    /* Compact ledger styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥤 MS MAA VINDHYAWASINI TRADERS (COCA COLA)")
st.caption(
    "Bill-Wise Ledger System - Auto Generated Bill Code (NAME + SERIAL NO)"
)


# ------------------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------------------
DB_FILE = "khatabook_billwise_v6.db"


def init_db():

    conn = sqlite3.connect(DB_FILE)
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

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        "SELECT * FROM bills ORDER BY Bill_ID DESC",
        conn,
    )

    conn.close()

    return df


def get_all_payments():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        "SELECT * FROM payments ORDER BY Payment_ID DESC",
        conn,
    )

    conn.close()

    return df


def get_managers():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        "SELECT name FROM managers ORDER BY name ASC",
        conn,
    )

    conn.close()

    if df.empty:
        return ["Default Manager"]

    return df["name"].tolist()


def get_outlets():

    conn = sqlite3.connect(DB_FILE)
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


# ------------------------------------------------------------------------------
# AUTO BILL CODE
# ------------------------------------------------------------------------------
def generate_auto_code_backend(outlet_name):

    clean_name = (
        "".join(
            e for e in outlet_name
            if e.isalnum()
        ).upper()
        if outlet_name
        else "BILL"
    )

    if not clean_name:
        clean_name = "BILL"

    short_code = clean_name[:5]

    conn = sqlite3.connect(DB_FILE)
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


# ------------------------------------------------------------------------------
# SAVE BILL
# ------------------------------------------------------------------------------
def save_bill_to_db(
    date_str,
    mgr,
    outlet,
    amount,
    note,
):

    bill_no = generate_auto_code_backend(outlet)

    conn = sqlite3.connect(DB_FILE)
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
            outlet,
            amount,
            amount,
            note,
        ),
    )

    conn.commit()
    conn.close()

    return bill_no


# ------------------------------------------------------------------------------
# UPDATE BILL
# ------------------------------------------------------------------------------
def update_bill_in_db(
    bill_no,
    date_str,
    mgr,
    outlet,
    amount,
    note,
):

    conn = sqlite3.connect(DB_FILE)
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


# ------------------------------------------------------------------------------
# DAYS PENDING
# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
# RECORD PAYMENT
# ------------------------------------------------------------------------------
def record_bill_payment(
    bill_no,
    date_str,
    outlet,
    mgr,
    paid_amt,
    mode,
    is_full,
):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

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

    if row:

        bill_amt, curr_paid, curr_bal = row

        if is_full:
            actual_payment = curr_bal
        else:
            actual_payment = min(
                paid_amt,
                curr_bal,
            )

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

    conn.close()


# ------------------------------------------------------------------------------
# DELETE BILL
# ------------------------------------------------------------------------------
def delete_bill_from_db(bill_no):

    conn = sqlite3.connect(DB_FILE)
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


# ------------------------------------------------------------------------------
# DELETE PAYMENT
# ------------------------------------------------------------------------------
def delete_payment_from_db(
    pay_id,
    bill_no,
    amt,
):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute(
        """
        DELETE FROM payments
        WHERE Payment_ID = ?
        """,
        (pay_id,),
    )

    c.execute(
        """
        SELECT
            Bill_Amount,
            Paid_Amount
        FROM bills
        WHERE Bill_No = ?
        """,
        (bill_no,),
    )

    row = c.fetchone()

    if row:

        b_amt, p_amt = row

        n_paid = max(
            0.0,
            p_amt - amt,
        )

        n_bal = b_amt - n_paid

        if n_bal <= 0:
            n_status = "🟢 PAID"

        elif n_paid == 0:
            n_status = "🔴 UNPAID"

        else:
            n_status = "🔴 PARTIAL"

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
                n_paid,
                n_bal,
                n_status,
                bill_no,
            ),
        )

    conn.commit()
    conn.close()


# ------------------------------------------------------------------------------
# SAVE MANAGER
# ------------------------------------------------------------------------------
def save_manager_to_db(mgr_str):

    clean_mgr = mgr_str.strip().title()

    if clean_mgr:

        conn = sqlite3.connect(DB_FILE)
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


# ------------------------------------------------------------------------------
# INITIALIZE DATABASE
# ------------------------------------------------------------------------------
init_db()


# ------------------------------------------------------------------------------
# PDF REPORT GENERATOR
# ------------------------------------------------------------------------------
def generate_pdf_report(
    df_data,
    subtitle_info="",
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18,
        leftMargin=18,
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
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
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
        textColor=colors.HexColor("#166534"),
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
            "MS MAA VINDHYAWASINI TRADERS",
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
        "Dues Days",
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

        is_paid = float(row["Balance"]) <= 0

        days_pending = (
            0
            if is_paid
            else calculate_days_pending(
                str(row["Date"])
            )
        )

        status_style = (
            green_status_style
            if "PAID" in status and "UNPAID" not in status
            else red_status_style
        )

        balance_style = (
            green_status_style
            if float(row["Balance"]) <= 0
            else red_balance_style
        )

        dues_style = (
            green_status_style
            if is_paid
            else red_status_style
        )

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
                Paragraph(
                    f"{days_pending} Days",
                    dues_style,
                ),
            ]
        )

    t = Table(
        table_data,
        colWidths=[
            63,
            53,
            105,
            63,
            63,
            65,
            63,
            55,
        ],
        repeatRows=1,
    )

    table_style_commands = [
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
            "PADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    for pdf_row_index, (_, pdf_row) in enumerate(
        df_data.iterrows(),
        start=1,
    ):

        if float(pdf_row["Balance"]) <= 0:

            table_style_commands.extend(
                [
                    (
                        "BACKGROUND",
                        (0, pdf_row_index),
                        (-1, pdf_row_index),
                        colors.HexColor("#DCFCE7"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, pdf_row_index),
                        (-1, pdf_row_index),
                        colors.HexColor("#166534"),
                    ),
                ]
            )

    t.setStyle(
        TableStyle(table_style_commands)
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


# ------------------------------------------------------------------------------
# FETCH DATA
# ------------------------------------------------------------------------------
managers_list = get_managers()
outlets_list = get_outlets()
bills_df = get_all_bills()
payments_df = get_all_payments()


# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------
with st.sidebar:

    st.header("⚙️ Master Settings")

    with st.expander("👤 Manager Setup"):

        new_mgr = st.text_input(
            "Add New Sales Manager"
        )

        if st.button("Save Manager"):

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


# ------------------------------------------------------------------------------
# TRANSACTION SECTION
# ------------------------------------------------------------------------------
st.markdown("---")

col_left, col_right = st.columns(2)


# ------------------------------------------------------------------------------
# CREATE BILL
# ------------------------------------------------------------------------------
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

    if selected_b_outlet == "+ Add New Customer/Outlet":

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


# ------------------------------------------------------------------------------
# PAYMENT RECEIVED
# ------------------------------------------------------------------------------
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

        conn = sqlite3.connect(DB_FILE)

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


# ------------------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
# TAB 1 - BILLS
# ------------------------------------------------------------------------------
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

        # ----------------------------------------------------------------------
        # COMPACT DETAILED BILL LEDGER
        # ----------------------------------------------------------------------
        st.markdown("#### 📋 Detailed Bills Ledger")

        ledger_df = df_view.copy()

        ledger_df["Dues_Days"] = ledger_df.apply(
            lambda r: (
                0
                if float(r["Balance"]) <= 0
                else calculate_days_pending(
                    str(r["Date"])
                )
            ),
            axis=1,
        )

        # Oldest / highest dues first
        ledger_df = ledger_df.sort_values(
            by="Dues_Days",
            ascending=False,
        )

        # Display-only dataframe
        ledger_display_df = ledger_df[
            [
                "Bill_No",
                "Manager_Name",
                "Date",
                "Outlet_Name",
                "Bill_Amount",
                "Paid_Amount",
                "Balance",
                "Status",
                "Dues_Days",
            ]
        ].copy()

        ledger_display_df = ledger_display_df.rename(
            columns={
                "Bill_No": "Bill Code",
                "Manager_Name": "Manager",
                "Date": "Date",
                "Outlet_Name": "Outlet",
                "Bill_Amount": "Bill Amt",
                "Paid_Amount": "Paid Amt",
                "Balance": "Balance",
                "Status": "Status",
                "Dues_Days": "Dues Days",
            }
        )

        # Currency formatting
        ledger_display_df["Bill Amt"] = (
            ledger_display_df["Bill Amt"]
            .apply(lambda x: f"Rs {x:,.2f}")
        )

        ledger_display_df["Paid Amt"] = (
            ledger_display_df["Paid Amt"]
            .apply(lambda x: f"Rs {x:,.2f}")
        )

        ledger_display_df["Balance"] = (
            ledger_display_df["Balance"]
            .apply(lambda x: f"Rs {x:,.2f}")
        )

        ledger_display_df["Dues Days"] = (
            ledger_display_df["Dues Days"]
            .apply(lambda x: f"{int(x)} Days")
        )

        # ----------------------------------------------------------------------
        # SCROLLABLE COMPACT TABLE
        # ----------------------------------------------------------------------
        st.dataframe(
            ledger_display_df,
            use_container_width=True,
            hide_index=True,
            height=430,
            column_config={
                "Bill Code": st.column_config.TextColumn(
                    "🧾 Bill Code",
                    width="small",
                ),
                "Manager": st.column_config.TextColumn(
                    "👤 Manager",
                    width="small",
                ),
                "Date": st.column_config.TextColumn(
                    "📅 Date",
                    width="small",
                ),
                "Outlet": st.column_config.TextColumn(
                    "🏪 Outlet",
                    width="medium",
                ),
                "Bill Amt": st.column_config.TextColumn(
                    "💰 Bill Amt",
                    width="small",
                ),
                "Paid Amt": st.column_config.TextColumn(
                    "🟢 Paid",
                    width="small",
                ),
                "Balance": st.column_config.TextColumn(
                    "🔴 Balance",
                    width="small",
                ),
                "Status": st.column_config.TextColumn(
                    "📌 Status",
                    width="small",
                ),
                "Dues Days": st.column_config.TextColumn(
                    "⏰ Dues",
                    width="small",
                ),
            },
        )

        # ----------------------------------------------------------------------
        # BILL ACTION
        # ----------------------------------------------------------------------
        st.markdown("##### ✏️ Bill Action")

        action_options = []

        for _, action_row in ledger_df.iterrows():

            action_options.append(
                f"{action_row['Bill_No']} | "
                f"{action_row['Outlet_Name']} | "
                f"Balance Rs {action_row['Balance']:,.2f}"
            )

        if action_options:

            selected_action = st.selectbox(
                "Select Bill for Edit / Delete:",
                action_options,
                key="compact_bill_action_select",
            )

            selected_action_bill_no = (
                selected_action
                .split("|")[0]
                .strip()
            )

            selected_action_rows = ledger_df[
                ledger_df["Bill_No"]
                == selected_action_bill_no
            ]

            if not selected_action_rows.empty:

                action_row = (
                    selected_action_rows.iloc[0]
                )

                action_col1, action_col2 = st.columns(2)

                # ------------------------------------------------------------------
                # EDIT
                # ------------------------------------------------------------------
                with action_col1:

                    if st.button(
                        "✏️ Edit Selected Bill",
                        use_container_width=True,
                        key="compact_edit_bill_button",
                    ):

                        st.session_state[
                            f"editing_bill_{selected_action_bill_no}"
                        ] = True

                        st.rerun()

                # ------------------------------------------------------------------
                # DELETE
                # ------------------------------------------------------------------
                with action_col2:

                    if st.button(
                        "🗑️ Delete Selected Bill",
                        use_container_width=True,
                        key="compact_delete_bill_button",
                    ):

                        st.session_state[
                            f"confirm_delete_bill_{selected_action_bill_no}"
                        ] = True

                        st.rerun()

                # ------------------------------------------------------------------
                # EDIT FORM
                # ------------------------------------------------------------------
                if st.session_state.get(
                    f"editing_bill_{selected_action_bill_no}",
                    False,
                ):

                    st.markdown(
                        f"""
                        <div class="edit-card">
                            <h4 style="color:#B7791F; margin:0;">
                                ✏️ MODIFY BILL:
                                {selected_action_bill_no}
                            </h4>
                            <p style="margin:5px 0 0 0;">
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
                                action_row["Date"],
                                "%d-%m-%Y",
                            ),
                            format="DD/MM/YYYY",
                            key=(
                                f"compact_edit_date_"
                                f"{selected_action_bill_no}"
                            ),
                        )

                        edit_manager = st.selectbox(
                            "Sales Manager",
                            managers_list,
                            index=(
                                managers_list.index(
                                    action_row["Manager_Name"]
                                )
                                if action_row["Manager_Name"]
                                in managers_list
                                else 0
                            ),
                            key=(
                                f"compact_edit_mgr_"
                                f"{selected_action_bill_no}"
                            ),
                        )

                    with edit_col2:

                        edit_outlet = st.text_input(
                            "Customer / Outlet Name",
                            value=action_row["Outlet_Name"],
                            key=(
                                f"compact_edit_outlet_"
                                f"{selected_action_bill_no}"
                            ),
                        )

                        edit_amount = st.number_input(
                            "Bill Amount (Rs)",
                            min_value=float(
                                action_row["Paid_Amount"]
                            ),
                            value=float(
                                action_row["Bill_Amount"]
                            ),
                            step=50.0,
                            key=(
                                f"compact_edit_amount_"
                                f"{selected_action_bill_no}"
                            ),
                        )

                    edit_note = st.text_input(
                        "Bill Details / Goods Note",
                        value=(
                            action_row["Note"]
                            if action_row["Note"]
                            else ""
                        ),
                        key=(
                            f"compact_edit_note_"
                            f"{selected_action_bill_no}"
                        ),
                    )

                    save_edit_col, cancel_edit_col = st.columns(2)

                    with save_edit_col:

                        if st.button(
                            "💾 Save Changes",
                            key=(
                                f"compact_save_edit_"
                                f"{selected_action_bill_no}"
                            ),
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
                                    action_row["Paid_Amount"]
                                )
                            ):

                                st.error(
                                    f"Bill amount cannot be "
                                    f"less than already paid "
                                    f"amount Rs "
                                    f"{action_row['Paid_Amount']:,.2f}."
                                )

                            else:

                                success, message = (
                                    update_bill_in_db(
                                        selected_action_bill_no,
                                        edit_date.strftime(
                                            "%d-%m-%Y"
                                        ),
                                        edit_manager,
                                        new_outlet,
                                        float(edit_amount),
                                        edit_note,
                                    )
                                )

                                if success:

                                    st.success(
                                        f"✅ Bill "
                                        f"{selected_action_bill_no} "
                                        f"modified successfully!"
                                    )

                                    st.session_state[
                                        f"editing_bill_{selected_action_bill_no}"
                                    ] = False

                                    st.rerun()

                                else:

                                    st.error(message)

                    with cancel_edit_col:

                        if st.button(
                            "❌ Cancel",
                            key=(
                                f"compact_cancel_edit_"
                                f"{selected_action_bill_no}"
                            ),
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"editing_bill_{selected_action_bill_no}"
                            ] = False

                            st.rerun()

                # ------------------------------------------------------------------
                # DELETE CONFIRMATION
                # ------------------------------------------------------------------
                if st.session_state.get(
                    f"confirm_delete_bill_{selected_action_bill_no}",
                    False,
                ):

                    st.markdown(
                        f"""
                        <div class="delete-card">
                            <h4 style="color:#B91C1C; margin:0;">
                                ⚠️ DELETE CONFIRMATION
                            </h4>

                            <p style="margin:5px 0 0 0;">
                                Are you sure you want to delete
                                Bill <b>{selected_action_bill_no}</b>
                                for
                                <b>{action_row['Outlet_Name']}</b>?
                                <br><br>
                                Is bill ke saath associated
                                payment history bhi delete ho jayegi.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    delete_yes_col, delete_no_col = st.columns(2)

                    with delete_yes_col:

                        if st.button(
                            "✅ Yes, Delete Bill",
                            key=(
                                f"compact_confirm_delete_"
                                f"{selected_action_bill_no}"
                            ),
                            use_container_width=True,
                        ):

                            delete_bill_from_db(
                                selected_action_bill_no
                            )

                            st.session_state[
                                f"confirm_delete_bill_{selected_action_bill_no}"
                            ] = False

                            st.success(
                                f"Bill "
                                f"{selected_action_bill_no} "
                                f"deleted successfully!"
                            )

                            st.rerun()

                    with delete_no_col:

                        if st.button(
                            "❌ Cancel",
                            key=(
                                f"compact_cancel_delete_"
                                f"{selected_action_bill_no}"
                            ),
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"confirm_delete_bill_{selected_action_bill_no}"
                            ] = False

                            st.rerun()

        # ----------------------------------------------------------------------
        # PDF EXPORT
        # HIGHEST DUES DAYS FIRST
        # ----------------------------------------------------------------------
        st.markdown("---")

        pdf_df = df_view.copy()

        if not pdf_df.empty:

            pdf_df["_Dues_Days"] = pdf_df.apply(
                lambda r: (
                    0
                    if float(r["Balance"]) <= 0
                    else calculate_days_pending(
                        str(r["Date"])
                    )
                ),
                axis=1,
            )

            pdf_df = pdf_df.sort_values(
                by="_Dues_Days",
                ascending=False,
            )

            pdf_df = pdf_df.drop(
                columns=["_Dues_Days"]
            )

        rep_sub = (
            f"Outlet: {selected_outlet_filter} | "
            f"Manager: {selected_mgr_filter}"
        )

        pdf_bytes = generate_pdf_report(
            pdf_df,
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

        # ----------------------------------------------------------------------
        # WHATSAPP OUTLET-WISE WRITTEN MESSAGE
        # ----------------------------------------------------------------------
        st.markdown("---")

        st.markdown(
            "#### 📲 Outlet-wise WhatsApp Message"
        )

        wa_outlet_col1, wa_outlet_col2 = st.columns(2)

        with wa_outlet_col1:

            wa_outlet_options = sorted(
                df_view["Outlet_Name"]
                .dropna()
                .unique()
                .tolist()
            )

            selected_wa_outlet = st.selectbox(
                "Select Outlet for WhatsApp Message:",
                wa_outlet_options,
                key="wa_outlet_select",
            )

        with wa_outlet_col2:

            wa_phone = st.text_input(
                "Customer Mobile No.",
                placeholder="91XXXXXXXXXX",
                key="wa_outlet_phone",
            )

        if st.button(
            "💬 Generate Outlet-wise WhatsApp Message",
            use_container_width=True,
        ):

            if not wa_phone.strip():

                st.warning(
                    "Please enter customer mobile number."
                )

            else:

                outlet_df = df_view[
                    df_view["Outlet_Name"]
                    == selected_wa_outlet
                ].copy()

                outlet_df["_Dues_Days"] = outlet_df.apply(
                    lambda r: (
                        0
                        if float(r["Balance"]) <= 0
                        else calculate_days_pending(
                            str(r["Date"])
                        )
                    ),
                    axis=1,
                )

                outlet_df = outlet_df.sort_values(
                    by="_Dues_Days",
                    ascending=False,
                )

                total_bill_amount = float(
                    outlet_df["Bill_Amount"].sum()
                )

                total_paid_amount = float(
                    outlet_df["Paid_Amount"].sum()
                )

                total_balance = float(
                    outlet_df["Balance"].sum()
                )

                msg = (
                    "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
                    "*OUTLET-WISE BILL STATEMENT / PAYMENT STATUS*\n"
                    "-----------------------------------\n"
                    f"🏪 *Outlet:* {selected_wa_outlet}\n"
                    f"📅 *Statement Date:* "
                    f"{datetime.now().strftime('%d-%m-%Y')}\n"
                    "-----------------------------------\n"
                )

                for _, wa_row in outlet_df.iterrows():

                    wa_is_paid = (
                        float(
                            wa_row["Balance"]
                        ) <= 0
                    )

                    wa_dues_days = (
                        0
                        if wa_is_paid
                        else calculate_days_pending(
                            str(
                                wa_row["Date"]
                            )
                        )
                    )

                    wa_status = str(
                        wa_row["Status"]
                    )

                    msg += (
                        f"\n🧾 *Bill Code:* "
                        f"{wa_row['Bill_No']}\n"
                        f"📅 *Bill Date:* "
                        f"{wa_row['Date']}\n"
                        f"👤 *Sales Manager:* "
                        f"{wa_row['Manager_Name']}\n"
                        f"💰 *Bill Amount:* "
                        f"Rs {wa_row['Bill_Amount']:,.2f}\n"
                        f"🟢 *Paid Amount:* "
                        f"Rs {wa_row['Paid_Amount']:,.2f}\n"
                        f"🔴 *Balance Due:* "
                        f"Rs {wa_row['Balance']:,.2f}\n"
                        f"📌 *Status:* "
                        f"{wa_status}\n"
                        f"⏰ *Dues Days:* "
                        f"{wa_dues_days} Days\n"
                        "-----------------------------\n"
                    )

                msg += (
                    "\n*📊 OUTLET TOTAL SUMMARY*\n"
                    "-----------------------------------\n"
                    f"💰 *Total Bill Amount:* "
                    f"Rs {total_bill_amount:,.2f}\n"
                    f"🟢 *Total Paid Amount:* "
                    f"Rs {total_paid_amount:,.2f}\n"
                    f"🔴 *Total Balance Due:* "
                    f"Rs {total_balance:,.2f}\n"
                    "-----------------------------------\n"
                )

                if total_balance <= 0:

                    msg += (
                        "✅ *All bills are fully paid.*\n"
                        "Thank you for your payment! 🙏\n"
                    )

                else:

                    msg += (
                        "⚠️ *Payment is pending against this outlet.*\n"
                        "Please clear the outstanding amount.\n"
                    )

                msg += (
                    "-----------------------------------\n"
                    "*MS MAA VINDHYAWASINI TRADERS*\n"
                    "Authorized Coca-Cola Distributor"
                )

                encoded_msg = urllib.parse.quote(
                    msg
                )

                clean_phone = (
                    wa_phone.strip()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("+", "")
                )

                wa_link = (
                    "https://api.whatsapp.com/send"
                    "?phone="
                    f"{clean_phone}"
                    f"&text={encoded_msg}"
                )

                st.markdown(
                    f"""
                    <a href="{wa_link}"
                       target="_blank"
                       style="
                           display:inline-block;
                           background-color:#25D366;
                           color:white;
                           padding:12px 20px;
                           border-radius:8px;
                           text-decoration:none;
                           font-weight:bold;
                           font-size:16px;
                       ">
                       💬 Open WhatsApp & Send Outlet Statement
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

                st.success(
                    "WhatsApp outlet-wise statement तैयार है। "
                    "Button पर click करके भेज सकते हैं।"
                )


# ------------------------------------------------------------------------------
# TAB 2 - PAYMENTS HISTORY
# ------------------------------------------------------------------------------
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

                if pc7.button(
                    "🗑️",
                    key=f"del_p_{p_row['Payment_ID']}",
                    help="Delete payment entry",
                ):

                    st.session_state[
                        f"confirm_delete_payment_{p_row['Payment_ID']}"
                    ] = True

                    st.rerun()

                if st.session_state.get(
                    f"confirm_delete_payment_{p_row['Payment_ID']}",
                    False,
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
                                p_row["Amount_Paid"],
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

                if rec_wa_phone.strip():

                    msg = (
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
                        f"Rs "
                        f"{latest_pay['Amount_Paid']:,.2f}\n"
                        f"💳 *Payment Mode:* "
                        f"{latest_pay['Payment_Mode']}\n"
                        "-----------------------------------\n"
                        "Thank you for your payment! "
                        "(धन्यवाद!)\n"
                    )

                    encoded_msg = urllib.parse.quote(
                        msg
                    )

                    clean_phone = (
                        rec_wa_phone.strip()
                        .replace(" ", "")
                        .replace("-", "")
                        .replace("+", "")
                    )

                    wa_link = (
                        "https://api.whatsapp.com/send"
                        "?phone="
                        f"{clean_phone}"
                        f"&text={encoded_msg}"
                    )

                    st.markdown(
                        f"""
                        <a href="{wa_link}"
                           target="_blank"
                           style="
                               display:inline-block;
                               background-color:#25D366;
                               color:white;
                               padding:12px 20px;
                               border-radius:8px;
                               text-decoration:none;
                               font-weight:bold;
                               font-size:16px;
                           ">
                           💬 Open WhatsApp & Send Payment Receipt
                        </a>
                        """,
                        unsafe_allow_html=True,
                    )

                else:

                    st.warning(
                        "Please enter a valid phone number!"
                    )
