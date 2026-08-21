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
    .paid-row {
        background-color: #d4edda !important;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        color: #155724;
    }
    .dues-row {
        background-color: #f8d7da !important;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        color: #721c24;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🥤 MS MAA VINDHYAWASINI TRADERS (COCA COLA)")
st.caption(
    "Manage sales managers, outlets/customers, debit/credit entries, due days,"
    " and export reports"
)

# ------------------------------------------------------------------------------
# 1. DATABASE MANAGEMENT
# ------------------------------------------------------------------------------
DB_FILE = "khatabook.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT,
            Manager_Name TEXT,
            Outlet_Name TEXT,
            Type TEXT,
            Debit REAL,
            Credit REAL,
            Balance REAL,
            Note TEXT
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


def refresh_state_from_db():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query(
      "SELECT ID, Date, Manager_Name as 'Manager Name', Outlet_Name as 'Outlet"
      " Name', Type, Debit as 'Debit (You Gave)', Credit as 'Credit (You Got)',"
      " Balance, Note FROM ledger ORDER BY ID ASC",
      conn,
  )
  mgr_df = pd.read_sql_query("SELECT name FROM managers", conn)
  conn.close()

  managers_list = (
      mgr_df["name"].tolist() if not mgr_df.empty else ["Default Manager"]
  )
  outlets_list = (
      sorted(list(df["Outlet Name"].dropna().unique())) if not df.empty else []
  )

  outlet_mgr_map = {}
  if not df.empty:
    for _, row in df.iterrows():
      outlet_mgr_map[row["Outlet Name"]] = row["Manager Name"]

  # Status Column जोड़ना (Balance > 0 -> DUES, Otherwise -> PAID)
  if not df.empty:
    df["Status"] = df["Balance"].apply(
        lambda b: "🔴 DUES" if b > 0 else "🟢 PAID"
    )
  else:
    df["Status"] = []

  st.session_state.ledger = df
  st.session_state.managers_list = managers_list
  st.session_state.outlets_list = outlets_list
  st.session_state.outlet_manager_map = outlet_mgr_map


def save_entry_to_db(entry):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      """
        INSERT INTO ledger (Date, Manager_Name, Outlet_Name, Type, Debit, Credit, Balance, Note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          entry["Date"],
          entry["Manager Name"],
          entry["Outlet Name"],
          entry["Type"],
          entry["Debit (You Gave)"],
          entry["Credit (You Got)"],
          entry["Balance"],
          entry["Note"],
      ),
  )
  conn.commit()
  conn.close()
  recalculate_balances_in_db()


def recalculate_balances_in_db():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query("SELECT * FROM ledger ORDER BY ID ASC", conn)

  if not df.empty:
    c = conn.cursor()
    for outlet in df["Outlet_Name"].unique():
      outlet_mask = df["Outlet_Name"] == outlet
      running_bal = 0.0

      for idx in df[outlet_mask].index:
        debit = float(df.at[idx, "Debit"])
        credit = float(df.at[idx, "Credit"])
        running_bal += debit - credit
        row_id = int(df.at[idx, "ID"])
        c.execute(
            "UPDATE ledger SET Balance = ? WHERE ID = ?", (running_bal, row_id)
        )
    conn.commit()
  conn.close()
  refresh_state_from_db()


def delete_entry_from_db(entry_id):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("DELETE FROM ledger WHERE ID = ?", (entry_id,))
  conn.commit()
  conn.close()
  recalculate_balances_in_db()


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
    refresh_state_from_db()


# Initialize DB and Load Session State
init_db()
if "ledger" not in st.session_state:
  refresh_state_from_db()

# ------------------------------------------------------------------------------
# 2. PDF GENERATION FUNCTION
# ------------------------------------------------------------------------------
def generate_pdf_report(
    df_data, report_title="CUSTOMER ACCOUNT STATEMENT", subtitle_info=""
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
  bold_cell_style = ParagraphStyle(
      "BoldCell", parent=table_cell_style, fontName="Helvetica-Bold"
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

  total_given = df_data["Debit (You Gave)"].sum()
  total_got = df_data["Credit (You Got)"].sum()
  total_due = total_given - total_got

  summary_data = [
      [
          Paragraph(
              "TOTAL DUES",
              ParagraphStyle(
                  "H1",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  textColor=colors.HexColor("#991B1B"),
                  alignment=1,
              ),
          ),
          Paragraph(
              "TOTAL RECEIVED",
              ParagraphStyle(
                  "H2",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  textColor=colors.HexColor("#166534"),
                  alignment=1,
              ),
          ),
          Paragraph(
              "NET BALANCE DUE",
              ParagraphStyle(
                  "H3",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  textColor=colors.HexColor("#1E3A8A"),
                  alignment=1,
              ),
          ),
      ],
      [
          Paragraph(
              f"Rs {total_given:,.2f}",
              ParagraphStyle(
                  "V1",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  fontSize=11,
                  textColor=colors.HexColor("#DC2626"),
                  alignment=1,
              ),
          ),
          Paragraph(
              f"Rs {total_got:,.2f}",
              ParagraphStyle(
                  "V2",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  fontSize=11,
                  textColor=colors.HexColor("#16A34A"),
                  alignment=1,
              ),
          ),
          Paragraph(
              f"Rs {total_due:,.2f}",
              ParagraphStyle(
                  "V3",
                  parent=table_cell_style,
                  fontName="Helvetica-Bold",
                  fontSize=11,
                  textColor=colors.HexColor("#1D4ED8"),
                  alignment=1,
              ),
          ),
      ],
  ]

  sum_table = Table(summary_data, colWidths=[180, 180, 185])
  sum_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FEF2F2")),
          ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F0FDF4")),
          ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EFF6FF")),
          ("BOX", (0, 0), (0, -1), 1, colors.HexColor("#FCA5A5")),
          ("BOX", (1, 0), (1, -1), 1, colors.HexColor("#86EFAC")),
          ("BOX", (2, 0), (2, -1), 1, colors.HexColor("#93C5FD")),
          ("PADDING", (0, 0), (-1, -1), 6),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
      ])
  )
  elements.append(sum_table)
  elements.append(Spacer(1, 12))

  headers = [
      "Date",
      "Manager",
      "Outlet/Customer",
      "Note",
      "DUES (Rs)",
      "RECEIVED (Rs)",
      "BALANCE (Rs)",
      "STATUS",
  ]
  table_data = [[Paragraph(h, table_hdr_style) for h in headers]]

  for _, row in df_data.iterrows():
    debit_val = row["Debit (You Gave)"]
    credit_val = row["Credit (You Got)"]

    debit_text = Paragraph(
        f"Rs {debit_val:,.2f}",
        red_cell_style if debit_val > 0 else table_cell_style,
    )
    credit_text = Paragraph(
        f"Rs {credit_val:,.2f}",
        green_cell_style if credit_val > 0 else table_cell_style,
    )
    balance_text = Paragraph(f"Rs {row['Balance']:,.2f}", bold_cell_style)
    status_text = Paragraph(
        row["Status"],
        red_cell_style if "DUES" in row["Status"] else green_cell_style,
    )

    table_data.append([
        Paragraph(str(row["Date"]), table_cell_style),
        Paragraph(str(row["Manager Name"]), table_cell_style),
        Paragraph(str(row["Outlet Name"]), table_cell_style),
        Paragraph(str(row["Note"]), table_cell_style),
        debit_text,
        credit_text,
        balance_text,
        status_text,
    ])

  t = Table(table_data, colWidths=[60, 65, 95, 105, 60, 60, 55, 45])
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

  elements.append(Spacer(1, 12))
  footer_style = ParagraphStyle(
      "DocFooter",
      parent=styles["Normal"],
      fontSize=8,
      textColor=colors.HexColor("#64748B"),
      alignment=1,
  )
  elements.append(
      Paragraph(
          "This is a computer-generated account statement. Thank you for your"
          " business!",
          footer_style,
      )
  )

  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


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
    st.write(", ".join(st.session_state.managers_list))

  with st.expander("💾 Backup CSV"):
    if not st.session_state.ledger.empty:
      csv_buf = st.session_state.ledger.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download CSV Backup",
          data=csv_buf,
          file_name=(
              "maa_vindhyawasini_khatabook_"
              f"{datetime.now().strftime('%d-%m-%Y')}.csv"
          ),
          mime="text/csv",
      )

# ------------------------------------------------------------------------------
# 4. TRANSACTIONS ENTRY SECTION
# ------------------------------------------------------------------------------
st.markdown("---")
col_left, col_right = st.columns(2)

# DUES ENTRY
with col_left:
  st.markdown(
      """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">🔴 ADD DUES (You Gave)</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record bill / debit entry assigned to Outlet</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  with st.form(key="udhari_form", clear_on_submit=True):
    u_date = st.date_input(
        "Date", datetime.now(), format="DD/MM/YYYY", key="u_date_key"
    )
    u_manager = st.selectbox(
        "Select Sales Manager",
        st.session_state.managers_list,
        key="u_mgr_select",
    )

    existing_outlets = [
        "+ Add New Customer/Outlet"
    ] + st.session_state.outlets_list
    selected_u_outlet = st.selectbox(
        "Customer / Outlet Name", existing_outlets, key="u_outlet_select"
    )

    if selected_u_outlet == "+ Add New Customer/Outlet":
      u_outlet = st.text_input("Enter New Store Name", key="u_outlet_text")
    else:
      u_outlet = selected_u_outlet

    u_amount = st.number_input(
        "Amount (Rs)", min_value=0.0, step=50.0, key="u_amt"
    )
    u_note = st.text_input("Details / Bill Notes (Optional)", key="u_note")

    btn_udhari = st.form_submit_button("🔴 Save Dues Entry")

  if btn_udhari:
    if not u_outlet.strip():
      st.error("Please enter a valid Outlet Name!")
    elif u_amount <= 0:
      st.error("Please enter a valid amount greater than zero!")
    else:
      final_outlet = u_outlet.strip().title()
      formatted_date = u_date.strftime("%d-%m-%Y")

      outlet_df = st.session_state.ledger[
          st.session_state.ledger["Outlet Name"] == final_outlet
      ]
      prev_balance = (
          outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0.0
      )
      new_balance = prev_balance + u_amount

      entry = {
          "Date": formatted_date,
          "Manager Name": u_manager,
          "Outlet Name": final_outlet,
          "Type": "🔴 Dues",
          "Debit (You Gave)": float(u_amount),
          "Credit (You Got)": 0.0,
          "Balance": float(new_balance),
          "Note": u_note if u_note else "Goods Bill",
      }

      save_entry_to_db(entry)
      st.success(f"🔴 Added Rs {u_amount:,.2f} dues for {final_outlet}")
      st.rerun()

# RECEIVED ENTRY
with col_right:
  st.markdown(
      """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">🟢 ADD RECEIVED (You Got)</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record payment collected from Outlet</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  if not st.session_state.outlets_list:
    st.info("No outlets available. Please add an entry on the left first.")
  else:
    with st.form(key="payment_form", clear_on_submit=True):
      p_date = st.date_input(
          "Date", datetime.now(), format="DD/MM/YYYY", key="p_date_key"
      )
      p_outlet = st.selectbox(
          "Select Customer / Outlet",
          st.session_state.outlets_list,
          key="p_outlet_select",
      )

      default_mgr = st.session_state.outlet_manager_map.get(
          p_outlet, st.session_state.managers_list[0]
      )
      p_manager = st.selectbox(
          "Sales Manager",
          st.session_state.managers_list,
          index=(
              st.session_state.managers_list.index(default_mgr)
              if default_mgr in st.session_state.managers_list
              else 0
          ),
          key="p_mgr_select",
      )

      p_outlet_df = st.session_state.ledger[
          st.session_state.ledger["Outlet Name"] == p_outlet
      ]
      current_due = (
          p_outlet_df["Balance"].iloc[-1] if not p_outlet_df.empty else 0.0
      )

      st.info(f"👉 **Current Due for {p_outlet}:** Rs {current_due:,.2f}")

      p_amount = st.number_input(
          "Received Amount (Rs)", min_value=0.0, step=50.0, key="p_amt"
      )
      p_mode = st.selectbox(
          "Payment Mode",
          ["Cash", "UPI / PhonePe / GPay", "Bank Transfer", "Cheque"],
          key="p_mode",
      )

      btn_payment = st.form_submit_button("🟢 Save Received Entry")

    if btn_payment:
      if p_amount <= 0:
        st.error("Please enter a valid amount greater than zero!")
      else:
        formatted_date = p_date.strftime("%d-%m-%Y")
        new_balance = current_due - p_amount

        entry = {
            "Date": formatted_date,
            "Manager Name": p_manager,
            "Outlet Name": p_outlet,
            "Type": "🟢 Received",
            "Debit (You Gave)": 0.0,
            "Credit (You Got)": float(p_amount),
            "Balance": float(new_balance),
            "Note": f"Payment ({p_mode})",
        }

        save_entry_to_db(entry)
        st.success(
            f"🟢 Received Rs {p_amount:,.2f} payment from {p_outlet}"
        )
        st.rerun()

# ------------------------------------------------------------------------------
# 5. DASHBOARD & DISPLAY SECTION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Ledger Dashboard & Dues Days Summary")

if st.session_state.ledger.empty:
  st.info("No ledger records available to display.")
else:
  f_col1, f_col2 = st.columns(2)

  with f_col1:
    selected_mgr_filter = st.selectbox(
        "Filter by Manager:",
        options=["All Managers"] + st.session_state.managers_list,
    )

  if selected_mgr_filter == "All Managers":
    filtered_outlets = ["All Outlets"] + st.session_state.outlets_list
  else:
    mgr_outlets = list(
        st.session_state.ledger[
            st.session_state.ledger["Manager Name"] == selected_mgr_filter
        ]["Outlet Name"].unique()
    )
    filtered_outlets = ["All Outlets"] + sorted(mgr_outlets)

  with f_col2:
    selected_outlet_filter = st.selectbox(
        "Filter by Outlet / Customer:", options=filtered_outlets
    )

  df_view = st.session_state.ledger.copy()
  if selected_mgr_filter != "All Managers":
    df_view = df_view[df_view["Manager Name"] == selected_mgr_filter]

  if selected_outlet_filter != "All Outlets":
    df_view = df_view[df_view["Outlet Name"] == selected_outlet_filter]

  tot_given = df_view["Debit (You Gave)"].sum()
  tot_got = df_view["Credit (You Got)"].sum()
  tot_due = tot_given - tot_got

  m1, m2, m3 = st.columns(3)
  m1.metric("Total Dues", f"Rs {tot_given:,.2f}")
  m2.metric("Total Received", f"Rs {tot_got:,.2f}")
  m3.metric("🔴 Net Balance Due", f"Rs {tot_due:,.2f}")

  # Outlet Pending Days Summary
  st.markdown("#### ⏳ Outlet Wise Dues & Pending Days")
  dues_data = []

  for outlet_name in st.session_state.outlets_list:
    o_df = st.session_state.ledger[
        st.session_state.ledger["Outlet Name"] == outlet_name
    ]
    if not o_df.empty:
      bal = o_df["Balance"].iloc[-1]
      if bal > 0:
        last_debit_entries = o_df[o_df["Debit (You Gave)"] > 0]
        if not last_debit_entries.empty:
          date_series = pd.to_datetime(
              last_debit_entries["Date"], format="%d-%m-%Y"
          )
          last_date = date_series.max()
          last_date_str = last_date.strftime("%d-%m-%Y")
          days_pending = (datetime.now() - last_date).days
        else:
          last_date_str = "N/A"
          days_pending = 0

        mgr_assigned = o_df["Manager Name"].iloc[-1]
        dues_data.append({
            "Outlet Name": outlet_name,
            "Manager": mgr_assigned,
            "Outstanding Due (Rs)": f"Rs {bal:,.2f}",
            "Last Bill Date": last_date_str,
            "Dues Pending Days": f"⏰ {days_pending} Days",
            "Status": "🔴 DUES",
        })

  if dues_data:
    st.dataframe(
        pd.DataFrame(dues_data), use_container_width=True, hide_index=True
    )
  else:
    st.success("🎉 No active outstanding dues for any outlet!")

  # Detailed Transactions Table
  st.markdown("#### 📋 Detailed Transactions")

  # Table Header
  h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7, h_col8, h_col9, h_col10 = (
      st.columns([0.8, 1.1, 1.3, 1.4, 1.8, 1.3, 1.3, 1.3, 1.1, 0.8])
  )
  h_col1.write("**ID**")
  h_col2.write("**Date**")
  h_col3.write("**Manager**")
  h_col4.write("**Outlet**")
  h_col5.write("**Note**")
  h_col6.write("**Dues (Rs)**")
  h_col7.write("**Received (Rs)**")
  h_col8.write("**Balance (Rs)**")
  h_col9.write("**Status**")
  h_col10.write("**Action**")

  st.divider()

  for idx, row in df_view.iterrows():
    # If total paid (Balance <= 0), apply green background style using HTML card container
    is_paid = row["Balance"] <= 0
    bg_style = (
        "background-color: #d4edda; border-radius: 5px; padding: 4px; margin-bottom: 3px;"
        if is_paid
        else "background-color: #f8d7da; border-radius: 5px; padding: 4px; margin-bottom: 3px;"
    )

    with st.container():
      c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(
          [0.8, 1.1, 1.3, 1.4, 1.8, 1.3, 1.3, 1.3, 1.1, 0.8]
      )

      c1.write(f"#{row['ID']}")
      c2.write(row["Date"])
      c3.write(row["Manager Name"])
      c4.write(row["Outlet Name"])
      c5.write(row["Note"])
      c6.write(f"Rs {row['Debit (You Gave)']:,.2f}")
      c7.write(f"Rs {row['Credit (You Got)']:,.2f}")
      c8.write(f"Rs {row['Balance']:,.2f}")

      if is_paid:
        c9.markdown("**🟢 PAID**")
      else:
        c9.markdown("**🔴 DUES**")

      if c10.button("🗑️", key=f"del_{row['ID']}"):
        delete_entry_from_db(row["ID"])
        st.success(f"Entry #{row['ID']} deleted!")
        st.rerun()

  # Export Section
  st.markdown("---")
  st.markdown("### 📄 Professional Export Options")
  exp_col1, exp_col2 = st.columns(2)

  with exp_col1:
    st.write("#### 📑 Customer PDF Statement")
    rep_sub = (
        f"Outlet: {selected_outlet_filter} | Manager: {selected_mgr_filter}"
    )

    pdf_bytes = generate_pdf_report(df_view, subtitle_info=rep_sub)

    st.download_button(
        label="📄 Download Professional PDF Statement",
        data=pdf_bytes,
        file_name=(
            f"Statement_{selected_outlet_filter}_"
            f"{datetime.now().strftime('%d%m%Y')}.pdf"
        ),
        mime="application/pdf",
    )

  with exp_col2:
    st.write("#### 💬 Direct WhatsApp Statement")
    wa_phone = st.text_input(
        "Customer WhatsApp Number", placeholder="91XXXXXXXXXX"
    )

    if st.button("📲 Generate WhatsApp Summary Link"):
      if wa_phone.strip():
        wa_text = "*🥤 MS MAA VINDHYAWASINI TRADERS*\n"
        wa_text += f"*Customer Statement:* {selected_outlet_filter}\n"
        wa_text += f"*Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
        wa_text += "-----------------------------------\n"
        wa_text += f"🔴 *Total Dues:* Rs {tot_given:,.2f}\n"
        wa_text += f"🟢 *Total Received:* Rs {tot_got:,.2f}\n"
        wa_text += f"📌 *NET DUE BALANCE:* Rs {tot_due:,.2f}\n"
        wa_text += (
            f"STATUS: {'🟢 FULLY PAID' if tot_due <= 0 else '🔴 PENDING DUES'}\n"
        )
        wa_text += "-----------------------------------\n"
        wa_text += (
            "Please clear the outstanding amount at the earliest. Thank you!"
        )

        encoded_text = urllib.parse.quote(wa_text)
        wa_url = (
            "https://api.whatsapp.com/send?phone="
            f"{wa_phone.strip()}&text={encoded_text}"
        )

        st.markdown(
            f"[👉 Click Here to Send Statement via WhatsApp]({wa_url})"
        )
      else:
        st.warning("Please enter a valid WhatsApp phone number!")
