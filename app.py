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
            Manager_Name TEXT,
            Date TEXT,
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
            Manager_Name,
            Date,
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
            mgr,
            date_str,
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
            Manager_Name = ?,
            Date = ?,
            Outlet_Name = ?,
            Bill_Amount = ?,
            Balance = ?,
            Status = ?,
            Note = ?
        WHERE Bill_No = ?
        """,
        (
            mgr,
            date_str,
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
        fontSize=7.5,
        leading=9,
    )

    green_status_style = ParagraphStyle(
        "GreenStatus",
        parent=table_cell_style,
        textColor=colors.HexColor("#166534"),
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
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

    # HEADERS - MANAGER NEXT TO BILL CODE, DUES DAYS SECOND LAST
    headers = [
        "Bill Code",
        "Manager",
        "Date",
        "Outlet/Customer",
        "Bill Amt (Rs)",
        "Paid Amt (Rs)",
        "Balance (Rs)",
        "Dues Days",
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
        is_paid = float(row["Balance"]) <= 0

        days_pending = (
            0
            if is_paid
            else calculate_days_pending(
                str(row["Date"])
            )
        )

        if (
            "PAID" in status
            and "UNPAID" not in status
        ):
            status_style = green_status_style
        else:
            status_style = red_status_style

        status_text = Paragraph(
            status,
            status_style,
        )

        if float(row["Balance"]) > 0:
            balance_style = red_balance_style
        else:
            balance_style = green_status_style

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
                    str(row["Manager_Name"]),
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
                    f"{days_pending} Days",
                    dues_style,
                ),
                status_text,
            ]
        )

    t = Table(
        table_data,
        colWidths=[
            55,
            65,
            50,
            90,
            55,
            55,
            55,
            45,
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
            "BACKGROUND",
            (0, 1),
            (-1, -1),
            colors.white,
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
        TableStyle(
            table_style_commands
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
        filter_mgr_payment = st.selectbox(
            "Filter by Sales Manager (Optional):",
            ["All Managers"] + managers_list,
            key="filter_mgr_payment_box"
        )

        conn = sqlite3.connect(DB_FILE)
        if filter_mgr_payment == "All Managers":
            outlets_for_mgr = outlets_list
        else:
            mgr_outlets_df = pd.read_sql_query(
                "SELECT DISTINCT Outlet_Name FROM bills WHERE Manager_Name = ? ORDER BY Outlet_Name ASC",
                conn,
                params=(filter_mgr_payment,)
            )
            outlets_for_mgr = mgr_outlets_df["Outlet_Name"].tolist()
        conn.close()

        if not outlets_for_mgr:
            st.warning("No outlets found for the selected manager.")
        else:
            p_outlet = st.selectbox(
                "Select Customer / Outlet for Payment:",
                outlets_for_mgr,
                key="p_outlet_select",
            )

            conn = sqlite3.connect(DB_FILE)
            if filter_mgr_payment == "All Managers":
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
            else:
                unpaid_bills_df = pd.read_sql_query(
                    """
                    SELECT *
                    FROM bills
                    WHERE Outlet_Name = ?
                    AND Manager_Name = ?
                    AND Balance > 0
                    ORDER BY Bill_ID ASC
                    """,
                    conn,
                    params=(p_outlet, filter_mgr_payment),
                )
            conn.close()

            total_net_dues_context = float(unpaid_bills_df["Balance"].sum()) if not unpaid_bills_df.empty else 0.0
            st.markdown(f"#### Total Net Dues: **Rs {total_net_dues_context:,.2f}**")

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
                    "Select Pending Bill:",
                    list(bill_options.keys()),
                    label_visibility="collapsed"
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
                            selected_bill["Bill_No"],
                            formatted_date,
                            p_outlet,
                            selected_bill["Manager_Name"],
                            float(p_amount),
                            p_mode,
                            is_full_flag,
                        )

                        st.success(
                            f"🟢 Successfully recorded payment of "
                            f"Rs {p_amount:,.2f} for "
                            f"Bill {selected_bill['Bill_No']}!"
                        )
                        st.rerun()


# ------------------------------------------------------------------------------
# DETAILED BILLS LEDGER (EXCEL TABLE GRID)
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Detailed Bills Ledger (Excel Table View)")

if bills_df.empty:
    st.info("No bills recorded in the system yet.")
else:
    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        ledger_mgr_filter = st.selectbox(
            "Filter Ledger by Manager:",
            ["All Managers"] + managers_list,
            key="ledger_mgr_filter"
        )
    with f_col2:
        ledger_outlet_filter = st.selectbox(
            "Filter Ledger by Outlet:",
            ["All Outlets"] + outlets_list,
            key="ledger_outlet_filter"
        )
    with f_col3:
        ledger_status_filter = st.selectbox(
            "Filter by Status:",
            ["All", "🔴 UNPAID / PARTIAL", "🟢 PAID"],
            key="ledger_status_filter"
        )

    # Apply filters to ledger dataframe
    filtered_df = bills_df.copy()
    if ledger_mgr_filter != "All Managers":
        filtered_df = filtered_df[filtered_df["Manager_Name"] == ledger_mgr_filter]
    if ledger_outlet_filter != "All Outlets":
        filtered_df = filtered_df[filtered_df["Outlet_Name"] == ledger_outlet_filter]
    if ledger_status_filter == "🔴 UNPAID / PARTIAL":
        filtered_df = filtered_df[filtered_df["Balance"] > 0]
    elif ledger_status_filter == "🟢 PAID":
        filtered_df = filtered_df[filtered_df["Balance"] <= 0]

    if filtered_df.empty:
        st.warning("No bills found matching the selected filter criteria.")
    else:
        # Calculate Dues Days for display view
        display_df = filtered_df.copy()
        display_df["Dues_Days"] = display_df.apply(
            lambda r: 0 if float(r["Balance"]) <= 0 else calculate_days_pending(r["Date"]),
            axis=1
        )
        display_df["Dues_Days_Str"] = display_df["Dues_Days"].astype(str) + " Days"

        # Re-arrange columns: Bill Code, Manager next to it, Date, Outlet, Amounts, Balance, Dues Days (Second last), Status, Note
        display_df = display_df[[
            "Bill_No",
            "Manager_Name",
            "Date",
            "Outlet_Name",
            "Bill_Amount",
            "Paid_Amount",
            "Balance",
            "Dues_Days_Str",
            "Status",
            "Note"
        ]]

        display_df.columns = [
            "Bill Code",
            "Manager Name",
            "Date",
            "Outlet / Customer",
            "Bill Amount (Rs)",
            "Paid Amount (Rs)",
            "Balance Due (Rs)",
            "Dues Days",
            "Status",
            "Note / Remarks"
        ]

        # Total Net Dues Card for Filtered View
        total_filtered_dues = float(filtered_df["Balance"].sum())
        st.markdown(f"### Total Net Dues (Filtered View): **Rs {total_filtered_dues:,.2f}**")

        # Excel-like interactive data table grid
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        # PDF Report Download Button for Ledger
        pdf_bytes = generate_pdf_report(
            filtered_df,
            subtitle_info=f"Manager: {ledger_mgr_filter} | Outlet: {ledger_outlet_filter}"
        )
        st.download_button(
            label="📄 Download Ledger PDF Report",
            data=pdf_bytes,
            file_name=f"ledger_report_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf",
        )


# ------------------------------------------------------------------------------
# EDIT / DELETE BILL SECTION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("✏️ Edit / Delete Existing Bill")

if not bills_df.empty:
    edit_col1, edit_col2 = st.columns(2)

    with edit_col1:
        st.markdown(
            """
            <div class="edit-card">
                <h4 style="color: #8A6D3B; margin:0;">✏️ Modify Bill Details</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_bill_to_edit = st.selectbox(
            "Select Bill Code to Edit:",
            bills_df["Bill_No"].tolist(),
            key="edit_bill_select"
        )

        current_bill_row = bills_df[bills_df["Bill_No"] == selected_bill_to_edit].iloc[0]

        edit_mgr = st.selectbox(
            "Sales Manager",
            managers_list,
            index=managers_list.index(current_bill_row["Manager_Name"]) if current_bill_row["Manager_Name"] in managers_list else 0,
            key="edit_mgr"
        )

        try:
            default_d = datetime.strptime(current_bill_row["Date"], "%d-%m-%Y")
        except Exception:
            default_d = datetime.now()

        edit_date = st.date_input(
            "Date",
            default_d,
            format="DD/MM/YYYY",
            key="edit_date"
        )

        edit_outlet = st.text_input(
            "Outlet Name",
            value=current_bill_row["Outlet_Name"],
            key="edit_outlet"
        )

        edit_amount = st.number_input(
            "Bill Amount (Rs)",
            min_value=0.0,
            value=float(current_bill_row["Bill_Amount"]),
            step=50.0,
            key="edit_amount"
        )

        edit_note = st.text_input(
            "Note / Remarks",
            value=str(current_bill_row["Note"] if current_bill_row["Note"] else ""),
            key="edit_note"
        )

        if st.button("💾 Update Bill Details", use_container_width=True):
            success, msg = update_bill_in_db(
                selected_bill_to_edit,
                edit_date.strftime("%d-%m-%Y"),
                edit_mgr,
                edit_outlet.strip().title(),
                float(edit_amount),
                edit_note
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with edit_col2:
        st.markdown(
            """
            <div class="delete-card">
                <h4 style="color: #DC2626; margin:0;">🗑️ Delete Bill Entry</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_bill_to_delete = st.selectbox(
            "Select Bill Code to Delete:",
            bills_df["Bill_No"].tolist(),
            key="delete_bill_select"
        )

        st.warning(
            f"⚠️ Deleting bill **{selected_bill_to_delete}** "
            "will also remove its associated payment history."
        )

        confirm_delete = st.checkbox(
            "I understand that this action is permanent",
            key="confirm_delete_box"
        )

        if st.button("🗑️ Delete Bill Permanently", use_container_width=True):
            if confirm_delete:
                delete_bill_from_db(selected_bill_to_delete)
                st.success(f"Deleted bill {selected_bill_to_delete} successfully.")
                st.rerun()
            else:
                st.error("Please check the confirmation box to proceed with deletion.")
