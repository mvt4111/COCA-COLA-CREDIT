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
    Spacer,
    Table,
    TableStyle,
)

import streamlit as st

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM STYLES
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
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🥤 MS MAA VINDHYAWASINI TRADERS (COCA COLA)")
st.caption(
    "Bill-Wise Ledger System with Instant Auto Bill Codes (NAME + SERIAL NO)"
)

# ------------------------------------------------------------------------------
# 1. DATABASE MANAGEMENT
# ------------------------------------------------------------------------------
DB_FILE = "khatabook_billwise_v5.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""
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
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            Payment_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT,
            Bill_No TEXT,
            Outlet_Name TEXT,
            Manager_Name TEXT,
            Amount_Paid REAL,
            Payment_Mode TEXT
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            name TEXT PRIMARY KEY
        )
    """)
  c.execute(
      "INSERT OR IGNORE INTO managers (name) VALUES ('Default Manager')"
  )
  conn.commit()
  conn.close()


def get_all_bills():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query("SELECT * FROM bills ORDER BY Bill_ID DESC", conn)
  conn.close()
  return df


def get_all_payments():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query(
      "SELECT * FROM payments ORDER BY Payment_ID DESC", conn
  )
  conn.close()
  return df


def get_managers():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query("SELECT name FROM managers", conn)
  conn.close()
  return (
      df["name"].tolist() if not df.empty else ["Default Manager"]
  )


def get_outlets():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("SELECT DISTINCT Outlet_Name FROM bills ORDER BY Outlet_Name ASC")
  outlets = [row[0] for row in c.fetchall() if row[0]]
  conn.close()
  return outlets


# NAME + SL NUMBER GENERATOR FUNCTION
def generate_bill_code(outlet_name):
  if not outlet_name or outlet_name.strip() == "":
    return "BILL-1"

  # नाम में से केवल अक्षर/नंबर लेना (Spaces या स्पेशल कैरेक्टर हटाकर)
  clean_name = (
      "".join(e for e in outlet_name if e.isalnum()).upper()
      if outlet_name
      else "BILL"
  )
  if len(clean_name) == 0:
    clean_name = "BILL"

  # अगर नाम बड़ा है तो पहले 4-5 अक्षर (जैसे: RAM, RAHUL)
  short_code = clean_name[:5]

  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  # चेक करें कि इस नाम के कितने बिल पहले से हैं
  c.execute(
      "SELECT COUNT(*) FROM bills WHERE Outlet_Name = ?", (outlet_name.strip(),)
  )
  count = c.fetchone()[0] + 1
  conn.close()

  # नाम + Serial No. (e.g., RAM-1, RAHUL-2)
  return f"{short_code}-{count}"


def save_bill_to_db(bill_no, date_str, mgr, outlet, amount, note):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      """
        INSERT INTO bills (Bill_No, Date, Manager_Name, Outlet_Name, Bill_Amount, Paid_Amount, Balance, Status, Note)
        VALUES (?, ?, ?, ?, ?, 0.0, ?, '🔴 UNPAID', ?)
    """,
      (bill_no, date_str, mgr, outlet, amount, amount, note),
  )
  conn.commit()
  conn.close()


def record_bill_payment(
    bill_no, date_str, outlet, mgr, paid_amt, mode, is_full
):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()

  c.execute(
      "SELECT Bill_Amount, Paid_Amount, Balance FROM bills WHERE Bill_No = ?",
      (bill_no,),
  )
  row = c.fetchone()
  if row:
    bill_amt, curr_paid, curr_bal = row

    if is_full:
      actual_payment = curr_bal
    else:
      actual_payment = min(paid_amt, curr_bal)

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
            SET Paid_Amount = ?, Balance = ?, Status = ? 
            WHERE Bill_No = ?
        """,
        (new_paid, new_bal, new_status, bill_no),
    )

    c.execute(
        """
            INSERT INTO payments (Date, Bill_No, Outlet_Name, Manager_Name, Amount_Paid, Payment_Mode)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (date_str, bill_no, outlet, mgr, actual_payment, mode),
    )

    conn.commit()
  conn.close()


def delete_bill_from_db(bill_no):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("DELETE FROM bills WHERE Bill_No = ?", (bill_no,))
  c.execute("DELETE FROM payments WHERE Bill_No = ?", (bill_no,))
  conn.commit()
  conn.close()


def delete_payment_from_db(pay_id, bill_no, amt):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("DELETE FROM payments WHERE Payment_ID = ?", (pay_id,))
  c.execute(
      "SELECT Bill_Amount, Paid_Amount FROM bills WHERE Bill_No = ?", (bill_no,)
  )
  row = c.fetchone()
  if row:
    b_amt, p_amt = row
    n_paid = max(0.0, p_amt - amt)
    n_bal = b_amt - n_paid
    n_status = (
        "🟢 PAID" if n_bal <= 0 else ("🔴 UNPAID" if n_paid == 0 else "🔴 PARTIAL")
    )
    c.execute(
        """
            UPDATE bills 
            SET Paid_Amount = ?, Balance = ?, Status = ? 
            WHERE Bill_No = ?
        """,
        (n_paid, n_bal, n_status, bill_no),
    )
  conn.commit()
  conn.close()


def save_manager_to_db(mgr_str):
  clean_mgr = mgr_str.strip().title()
  if clean_mgr:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO managers (name) VALUES (?)", (clean_mgr,)
    )
    conn.commit()
    conn.close()


init_db()


def calculate_days_pending(bill_date_str):
  try:
    b_date = datetime.strptime(bill_date_str, "%d-%m-%Y")
    days = (datetime.now() - b_date).days
    return max(0, days)
  except Exception:
    return 0


# ------------------------------------------------------------------------------
# 2. PDF REPORT GENERATOR
# ------------------------------------------------------------------------------
def generate_pdf_report(df_data, subtitle_info=""):
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

  elements.append(Paragraph("🥤 MS MAA VINDHYAWASINI TRADERS", title_style))
  elements.append(
      Paragraph(" AUTHORIZED COCA-COLA DISTRIBUTOR", sub_title_style)
  )
  elements.append(
      Paragraph(
          f"<b>Statement Info:</b> {subtitle_info} | <b>Date:</b>"
          f" {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
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
      "Dues Days",
      "Bill Amt (Rs)",
      "Paid Amt (Rs)",
      "Balance (Rs)",
      "Status",
  ]
  table_data = [[Paragraph(h, table_hdr_style) for h in headers]]

  for _, row in df_data.iterrows():
    days_p = (
        calculate_days_pending(row["Date"]) if row["Balance"] > 0 else "0"
    )
    days_str = f"{days_p} Days" if row["Balance"] > 0 else "PAID"
    status_text = Paragraph(
        row["Status"],
        green_cell_style if "PAID" in row["Status"] else red_cell_style,
    )

    table_data.append([
        Paragraph(str(row["Bill_No"]), table_cell_style),
        Paragraph(str(row["Date"]), table_cell_style),
        Paragraph(str(row["Outlet_Name"]), table_cell_style),
        Paragraph(
            days_str, red_cell_style if row["Balance"] > 0 else table_cell_style
        ),
        Paragraph(f"Rs {row['Bill_Amount']:,.2f}", table_cell_style),
        Paragraph(f"Rs {row['Paid_Amount']:,.2f}", green_cell_style),
        Paragraph(f"Rs {row['Balance']:,.2f}", red_cell_style),
        status_text,
    ])

  t = Table(table_data, colWidths=[65, 60, 110, 55, 65, 65, 65, 60])
  t.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
          ("ALIGN", (0, 0), (-1, -1), "LEFT"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
          (
              "ROWBACKGROUNDS",
              (0, 1),
              (-1, -1),
              [colors.white, colors.HexColor("#F8FAFC")],
          ),
          ("PADDING", (0, 0), (-1, -1), 4),
      ])
  )
  elements.append(t)

  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# Fetch Data Fresh Every Rerun
managers_list = get_managers()
outlets_list = get_outlets()
bills_df = get_all_bills()
payments_df = get_all_payments()

# ------------------------------------------------------------------------------
# 3. SIDEBAR SETUP
# ------------------------------------------------------------------------------
with st.sidebar:
  st.header("⚙️ Master Settings")

  with st.expander("👤 Manager Setup"):
    new_mgr = st.text_input("Add New Sales Manager")
    if st.button("Save Manager"):
      if new_mgr.strip():
        save_manager_to_db(new_mgr)
        st.success(f"Added Manager: {new_mgr}")
        st.rerun()

    st.divider()
    st.write("**Current Managers:**")
    st.write(", ".join(managers_list))

  with st.expander("💾 Backup CSV"):
    if not bills_df.empty:
      csv_buf = bills_df.to_csv(index=False).encode("utf-8")
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
# 4. TRANSACTIONS ENTRY SECTION
# ------------------------------------------------------------------------------
st.markdown("---")
col_left, col_right = st.columns(2)

# DUES ENTRY (NEW BILL)
with col_left:
  st.markdown(
      """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">🔴 CREATE NEW BILL / DUES</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record new bill entry against Outlet</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  b_date = st.date_input(
      "Bill Date", datetime.now(), format="DD/MM/YYYY", key="b_date_key"
  )
  b_manager = st.selectbox(
      "Select Sales Manager", managers_list, key="b_mgr_select"
  )

  existing_outlets = ["+ Add New Customer/Outlet"] + outlets_list
  selected_b_outlet = st.selectbox(
      "Customer / Outlet Name", existing_outlets, key="b_outlet_select"
  )

  if selected_b_outlet == "+ Add New Customer/Outlet":
    b_outlet = st.text_input(
        "Enter Store Name (दुकान/ग्राहक का नाम)",
        placeholder="e.g. RAM TRADERS",
        key="b_outlet_text",
    )
  else:
    b_outlet = selected_b_outlet

  # REAL-TIME AUTO CODE GENERATION (NAME + SL)
  auto_generated_code = generate_bill_code(b_outlet)

  b_no = st.text_input(
      "Auto Bill Code (नाम + सीरियल नंबर)",
      value=auto_generated_code,
      key="b_no_input",
      help="यह नाम और सीरियल नंबर के हिसाब से अपने आप बन रहा है।",
  )

  b_amount = st.number_input(
      "Bill Amount (Rs)", min_value=0.0, step=50.0, key="b_amt"
  )
  b_note = st.text_input("Bill Details / Goods Note (Optional)", key="b_note")

  if st.button("🔴 Save Bill Entry", use_container_width=True):
    if not b_outlet.strip():
      st.error("Please enter a valid Outlet Name!")
    elif b_amount <= 0:
      st.error("Please enter a valid amount greater than zero!")
    elif (
        not bills_df.empty
        and b_no.strip() in bills_df["Bill_No"].astype(str).values
    ):
      st.error(f"Bill Code '{b_no}' already exists! System generated a new code.")
    else:
      final_outlet = b_outlet.strip().title()
      formatted_date = b_date.strftime("%d-%m-%Y")

      save_bill_to_db(
          b_no.strip(),
          formatted_date,
          b_manager,
          final_outlet,
          float(b_amount),
          b_note if b_note else "Coca Cola Goods Bill",
      )
      st.success(
          f"🔴 Created Bill '{b_no}' for {final_outlet} of Rs {b_amount:,.2f}"
      )
      st.rerun()

# RECEIVED ENTRY (BILL-WISE PAYMENT CLEARANCE)
with col_right:
  st.markdown(
      """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">🟢 BILL-WISE PAYMENT RECEIVED</h3>
            <p style="margin:0; font-size:13px; color:#555;">Clear Full or Partial Payment against specific Bill</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  if not outlets_list:
    st.info("No active outlets found. Create a bill on the left first.")
  else:
    p_outlet = st.selectbox(
        "Select Customer / Outlet for Payment:",
        outlets_list,
        key="p_outlet_select",
    )

    # Fetch Unpaid Bills Fresh
    conn = sqlite3.connect(DB_FILE)
    unpaid_bills_df = pd.read_sql_query(
        "SELECT * FROM bills WHERE Outlet_Name = ? AND Balance > 0 ORDER BY"
        " Bill_ID ASC",
        conn,
        params=(p_outlet,),
    )
    conn.close()

    if unpaid_bills_df.empty:
      st.success(f"🎉 No outstanding unpaid bills for {p_outlet}!")
    else:
      bill_options = {}
      for _, row in unpaid_bills_df.iterrows():
        d_days = calculate_days_pending(row["Date"])
        label = f"{row['Bill_No']} | Date: {row['Date']} | ⏰ {d_days} Days Old | Balance Due: Rs {row['Balance']:,.2f}"
        bill_options[label] = row

      selected_bill_label = st.selectbox(
          "Select Pending Bill Code to Clear Payment:",
          list(bill_options.keys()),
      )
      selected_bill = bill_options[selected_bill_label]

      p_date = st.date_input(
          "Payment Date",
          datetime.now(),
          format="DD/MM/YYYY",
          key="p_date_key",
      )

      pay_type = st.radio(
          "Payment Type (भुगतान का प्रकार):",
          ["Full Bill Payment (पूरा बिल चुकता)", "Part Payment (आंशिक/किश्त)"],
          horizontal=True,
      )

      if pay_type == "Full Bill Payment (पूरा बिल चुकता)":
        p_amount = float(selected_bill["Balance"])
        st.info(
            f"✅ Full Amount Selected: **Rs {p_amount:,.2f}** for Bill"
            f" **{selected_bill['Bill_No']}**"
        )
      else:
        p_amount = st.number_input(
            "Enter Part Payment Amount (Rs)",
            min_value=0.0,
            max_value=float(selected_bill["Balance"]),
            step=50.0,
            key="p_amt_part",
        )

      p_mode = st.selectbox(
          "Payment Mode",
          ["Cash", "UPI / PhonePe / GPay", "Bank Transfer", "Cheque"],
          key="p_mode",
      )

      if st.button("🟢 Receive & Clear Payment", use_container_width=True):
        if p_amount <= 0:
          st.error("Please enter a valid amount greater than zero!")
        else:
          formatted_date = p_date.strftime("%d-%m-%Y")
          is_full_flag = pay_type == "Full Bill Payment (पूरा बिल चुकता)"

          record_bill_payment(
              str(selected_bill["Bill_No"]),
              formatted_date,
              p_outlet,
              str(selected_bill["Manager_Name"]),
              float(p_amount),
              p_mode,
              is_full_flag,
          )

          st.success(
              f"🟢 Payment of Rs {p_amount:,.2f} recorded for Bill"
              f" {selected_bill['Bill_No']}"
          )
          st.rerun()

# ------------------------------------------------------------------------------
# 5. DASHBOARD & TABS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Business Dashboard & Records")

tab_bills, tab_payments = st.tabs(
    ["📋 All Bills Ledger (बकाया बिल लिस्ट)", "🧾 Payments Received History (प्राप्त पेमेंट रसीदें)"]
)

# TAB 1: ALL BILLS
with tab_bills:
  if bills_df.empty:
    st.info("No bills recorded yet.")
  else:
    f_col1, f_col2 = st.columns(2)

    with f_col1:
      selected_mgr_filter = st.selectbox(
          "Filter by Manager:",
          options=["All Managers"] + managers_list,
          key="filter_mgr_tab1",
      )

    if selected_mgr_filter == "All Managers":
      filtered_outlets = ["All Outlets"] + outlets_list
    else:
      mgr_outlets = list(
          bills_df[bills_df["Manager_Name"] == selected_mgr_filter][
              "Outlet_Name"
          ].unique()
      )
      filtered_outlets = ["All Outlets"] + sorted(mgr_outlets)

    with f_col2:
      selected_outlet_filter = st.selectbox(
          "Filter by Outlet / Customer:",
          options=filtered_outlets,
          key="filter_outlet_tab1",
      )

    df_view = bills_df.copy()
    if selected_mgr_filter != "All Managers":
      df_view = df_view[df_view["Manager_Name"] == selected_mgr_filter]

    if selected_outlet_filter != "All Outlets":
      df_view = df_view[df_view["Outlet_Name"] == selected_outlet_filter]

    tot_bill = df_view["Bill_Amount"].sum()
    tot_paid = df_view["Paid_Amount"].sum()
    tot_due = df_view["Balance"].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Billed Amount", f"Rs {tot_bill:,.2f}")
    m2.metric("Total Paid Received", f"Rs {tot_paid:,.2f}")
    m3.metric("🔴 Total Net Dues Balance", f"Rs {tot_due:,.2f}")

    st.markdown("#### 📋 Detailed Bills")

    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7, h_col8, h_col9, h_col10 = (
        st.columns([1.1, 1.0, 1.3, 1.1, 1.1, 1.1, 1.1, 1.1, 1.0, 0.7])
    )
    h_col1.write("**Bill Code**")
    h_col2.write("**Date**")
    h_col3.write("**Outlet**")
    h_col4.write("**Manager**")
    h_col5.write("**⏰ Dues Days**")
    h_col6.write("**Bill Amt**")
    h_col7.write("**Paid Amt**")
    h_col8.write("**Balance**")
    h_col9.write("**Status**")
    h_col10.write("**Action**")

    st.divider()

    for idx, row in df_view.iterrows():
      is_paid = row["Balance"] <= 0
      days_p = calculate_days_pending(row["Date"]) if not is_paid else 0

      with st.container():
        c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(
            [1.1, 1.0, 1.3, 1.1, 1.1, 1.1, 1.1, 1.1, 1.0, 0.7]
        )

        c1.write(f"**{row['Bill_No']}**")
        c2.write(row["Date"])
        c3.write(row["Outlet_Name"])
        c4.write(row["Manager_Name"])

        if not is_paid:
          c5.markdown(f"**⏰ {days_p} Days**")
        else:
          c5.write("0 Days")

        c6.write(f"Rs {row['Bill_Amount']:,.2f}")
        c7.write(f"Rs {row['Paid_Amount']:,.2f}")
        c8.write(f"Rs {row['Balance']:,.2f}")

        if row["Status"] == "🟢 PAID":
          c9.markdown("**🟢 PAID**")
        elif row["Status"] == "🔴 PARTIAL":
          c9.markdown("**🔴 PARTIAL**")
        else:
          c9.markdown("**🔴 UNPAID**")

        if c10.button("🗑️", key=f"del_b_{row['Bill_No']}"):
          delete_bill_from_db(row["Bill_No"])
          st.success(f"Bill #{row['Bill_No']} deleted!")
          st.rerun()

    st.markdown("---")
    rep_sub = (
        f"Outlet: {selected_outlet_filter} | Manager: {selected_mgr_filter}"
    )
    pdf_bytes = generate_pdf_report(df_view, subtitle_info=rep_sub)

    st.download_button(
        label="📄 Download Bills PDF Statement",
        data=pdf_bytes,
        file_name=(
            f"Bill_Statement_{selected_outlet_filter}_"
            f"{datetime.now().strftime('%d%m%Y')}.pdf"
        ),
        mime="application/pdf",
    )

# TAB 2: PAYMENTS HISTORY
with tab_payments:
  st.markdown("### 🟢 History of All Received Payments")

  if payments_df.empty:
    st.info("No payments received yet.")
  else:
    total_rec = payments_df["Amount_Paid"].sum()
    st.metric("Total Payments Collected", f"Rs {total_rec:,.2f}")

    p_col1, p_col2, p_col3, p_col4, p_col5, p_col6, p_col7 = st.columns(
        [1.0, 1.2, 1.5, 1.2, 1.2, 1.2, 1.0]
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
        pc1, pc2, pc3, pc4, pc5, pc6, pc7 = st.columns(
            [1.0, 1.2, 1.5, 1.2, 1.2, 1.2, 1.0]
        )

        pc1.write(p_row["Date"])
        pc2.write(f"**{p_row['Bill_No']}**")
        pc3.write(p_row["Outlet_Name"])
        pc4.write(p_row["Manager_Name"])
        pc5.markdown(f"**🟢 Rs {p_row['Amount_Paid']:,.2f}**")
        pc6.write(p_row["Payment_Mode"])

        if pc7.button("🗑️", key=f"del_p_{p_row['Payment_ID']}"):
          delete_payment_from_db(
              p_row["Payment_ID"], p_row["Bill_No"], p_row["Amount_Paid"]
          )
          st.success("Payment entry removed!")
          st.rerun()

    st.markdown("---")
    st.markdown("#### 📲 Send Payment Receipt to Customer via WhatsApp")

    wa_p_col1, wa_p_col2 = st.columns(2)
    with wa_p_col1:
      rec_wa_phone = st.text_input(
          "Customer Mobile No",
          placeholder="91XXXXXXXXXX",
          key="rec_wa_phone_key",
      )
    with wa_p_col2:
      latest_pay = payments_df.iloc[0]
      if st.button("💬 Send Latest Payment Confirmation Receipt"):
        if rec_wa_phone.strip():
          msg = "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
          msg += "*PAYMENT RECEIPT (भुगतान रसीद)*\n"
          msg += "-----------------------------------\n"
          msg += f"👤 *Store Name:* {latest_pay['Outlet_Name']}\n"
          msg += f"🧾 *Bill Code:* {latest_pay['Bill_No']}\n"
          msg += f"📅 *Payment Date:* {latest_pay['Date']}\n"
          msg += f"🟢 *AMOUNT RECEIVED:* Rs {latest_pay['Amount_Paid']:,.2f}\n"
          msg += f"💳 *Payment Mode:* {latest_pay['Payment_Mode']}\n"
          msg += "-----------------------------------\n"
          msg += "Thank you for your payment! (धन्यवाद!)\n"

          encoded_msg = urllib.parse.quote(msg)
          wa_link = (
              "https://api.whatsapp.com/send?phone="
              f"{rec_wa_phone.strip()}&text={encoded_msg}"
          )

          st.markdown(
              f"[👉 Click Here to Send Payment Receipt on WhatsApp]({wa_link})"
          )
        else:
          st.warning("Please enter a valid phone number!")
