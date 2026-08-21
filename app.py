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

    headers = [
        "Bill Code",
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

        status_style = (
            green_status_style
            if ("PAID" in status and "UNPAID" not in status)
            else red_status_style
        )
        status_text = Paragraph(status, status_style)

        balance_style = (
            red_balance_style
            if float(row["Balance"]) > 0
            else green_status_style
        )
        dues_style = (
            green_status_style
            if is_paid
            else red_status_style
        )

        table_data.append(
            [
                Paragraph(str(row["Bill_No"]), table_cell_style),
                Paragraph(str(row["Date"]), table_cell_style),
                Paragraph(str(row["Outlet_Name"]), table_cell_style),
                Paragraph(f"Rs {row['Bill_Amount']:,.2f}", table_cell_style),
                Paragraph(f"Rs {row['Paid_Amount']:,.2f}", green_amount_style),
                Paragraph(f"Rs {row['Balance']:,.2f}", balance_style),
                Paragraph(f"{days_pending} Days", dues_style),
                status_text,
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
            55,
            63,
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

    t.setStyle(TableStyle(table_style_commands))
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
                label = (
                    f"{row['Bill_No']} | "
                    f"Date: {row['Date']} | "
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
                        f"Rs {p_amount:,.2f} for bill "
                        f"{selected_bill['Bill_No']}!"
                    )

                    st.rerun()


# ------------------------------------------------------------------------------
# BUSINESS DASHBOARD RECORDS (UPDATED TO TABLE WITH WHITE BACKGROUND)
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Business Ledger Records & Dashboard")

if not bills_df.empty:
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        filter_mgr = st.selectbox(
            "Filter by Sales Manager",
            ["All Managers"] + managers_list,
            key="filter_mgr_select"
        )
        
    with col_f2:
        filter_outlet = st.selectbox(
            "Filter by Outlet / Customer",
            ["All Outlets"] + outlets_list,
            key="filter_outlet_select"
        )

    filtered_df = bills_df.copy()

    if filter_mgr != "All Managers":
        filtered_df = filtered_df[filtered_df["Manager_Name"] == filter_mgr]

    if filter_outlet != "All Outlets":
        filtered_df = filtered_df[filtered_df["Outlet_Name"] == filter_outlet]

    if not filtered_df.empty:
        dash_df = filtered_df.copy()
        dash_df['Dues Days'] = dash_df['Date'].apply(calculate_days_pending)
        
        cols = list(dash_df.columns)
        if 'Dues Days' in cols:
            cols.remove('Dues Days')
            status_idx = cols.index('Status')
            cols.insert(status_idx, 'Dues Days')
            dash_df = dash_df[cols]

        st.dataframe(
            dash_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Bill_Amount": st.column_config.NumberColumn("Bill Amt (Rs)", format="₹%.2f"),
                "Paid_Amount": st.column_config.NumberColumn("Paid Amt (Rs)", format="₹%.2f"),
                "Balance": st.column_config.NumberColumn("Balance (Rs)", format="₹%.2f"),
            }
        )

        total_net_dues = float(filtered_df["Balance"].sum())
        st.markdown(
            f"<h3 style='text-align: right; color: #DC2626;'>TOTAL NET DUES: ₹ {total_net_dues:,.2f}</h3>",
            unsafe_allow_html=True
        )
    else:
        st.info("चयनित फ़िल्टर के आधार पर कोई रिकॉर्ड नहीं मिला।")
else:
    st.info("अभी कोई रिकॉर्ड दर्ज नहीं किया गया है।")
