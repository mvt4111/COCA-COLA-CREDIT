import io
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Coca-Cola Credit Tracker", page_icon="🥤", layout="wide"
)

st.title("🥤 Coca-Cola Distribution - Credit & Ledger App")
st.caption("500+ Outlets & Manager Wise Accounting Management")


# ------------------------------------------------------------------------------
# 1. HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def generate_pdf(dataframe: pd.DataFrame, total_dues_amount: float) -> io.BytesIO:
    """Generates a styled PDF report statement using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#D4001A"),
    )
    header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        textColor=colors.whitesmoke,
        fontSize=8,
        leading=10,
        alignment=1,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=1,
    )

    # Document Header
    elements.append(
        Paragraph(
            "<b>Coca-Cola Distribution - Account Statement</b>", title_style
        )
    )
    elements.append(
        Paragraph(
            f"Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            f"<b>Total Outstanding Dues: ₹ {total_dues_amount:,.2f}</b>",
            styles["Heading2"],
        )
    )
    elements.append(Spacer(1, 12))

    # Table Setup (Removed Category, Added Dues Days)
    headers = [
        "ID",
        "Date",
        "Outlet Name",
        "Manager",
        "Debit (₹)",
        "Credit (₹)",
        "Balance (₹)",
        "Dues (Days)",
    ]
    table_data = [[Paragraph(h, header_style) for h in headers]]

    for _, row in dataframe.iterrows():
        table_data.append([
            Paragraph(str(row["ID"]), cell_style),
            Paragraph(str(row["Date"]), cell_style),
            Paragraph(str(row["Outlet Name"]), cell_style),
            Paragraph(str(row["Manager"]), cell_style),
            Paragraph(f"{row['Udhari (Debit)']:,.2f}", cell_style),
            Paragraph(f"{row['Payment (Credit)']:,.2f}", cell_style),
            Paragraph(f"{row['Balance']:,.2f}", cell_style),
            Paragraph(str(row["Dues Days"]), cell_style),
        ])

    # Dynamic Column Widths for Letter Page
    col_widths = [30, 65, 120, 95, 68, 68, 68, 60]
    pdf_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    pdf_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D4001A")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.whitesmoke, colors.white],
            ),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    elements.append(pdf_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ------------------------------------------------------------------------------
# 2. STATE MANAGEMENT & BACKUP
# ------------------------------------------------------------------------------
if "ledger" not in st.session_state:
    st.session_state.ledger = pd.DataFrame(
        columns=[
            "ID",
            "Date",
            "Outlet Name",
            "Manager",
            "Udhari (Debit)",
            "Payment (Credit)",
            "Balance",
            "Due Date",
            "Dues Days",
        ]
    )

# Sidebar: CSV Import/Export Tools
with st.sidebar.expander("💾 Backup & Restore Data"):
    uploaded_file = st.file_uploader("Restore Ledger CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            st.session_state.ledger = pd.read_csv(uploaded_file)
            st.success("Ledger restored successfully!")
        except Exception as e:
            st.error(f"Error loading CSV: {e}")

    if not st.session_state.ledger.empty:
        csv_buffer = st.session_state.ledger.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Data (CSV)",
            data=csv_buffer,
            file_name=f"ledger_backup_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# ------------------------------------------------------------------------------
# 3. SIDEBAR FORM ENTRY
# ------------------------------------------------------------------------------
st.sidebar.header("➕ नई एंट्री दर्ज करें (New Entry)")

with st.sidebar.form(key="entry_form", clear_on_submit=True):
    entry_date = st.date_input("Entry Date (तारीख)", datetime.now())
    outlet_name = st.text_input("Outlet Name (दुकान का नाम)")
    manager = st.selectbox(
        "Assigned Manager",
        ["PIYUSH YADAV", "RUKSHAT ALAM", "SUMIT MGR", "PRAKASH MGR"],
    )
    trans_type = st.radio(
        "Transaction Type", ["Udhari (Debit)", "Payment Received (Credit)"]
    )
    amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)

    submit_button = st.form_submit_button("Save Entry (रजिस्टर करें)")

if submit_button:
    if not outlet_name.strip():
        st.sidebar.error("कृपया आउटलेट का नाम दर्ज करें!")
    else:
        debit = amount if trans_type == "Udhari (Debit)" else 0.0
        credit = amount if trans_type == "Payment Received (Credit)" else 0.0

        # Outlet Specific Data
        outlet_df = st.session_state.ledger[
            st.session_state.ledger["Outlet Name"] == outlet_name.strip()
        ]
        prev_balance = (
            outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0.0
        )
        current_balance = prev_balance + debit - credit

        # Calculate Dues Days logic
        if current_balance <= 0:
            due_date_str = "-"
            dues_days = 0
        else:
            if trans_type == "Udhari (Debit)" or outlet_df.empty:
                due_date_str = entry_date.strftime("%Y-%m-%d")
            else:
                due_date_str = (
                    outlet_df["Due Date"].iloc[-1]
                    if "Due Date" in outlet_df.columns
                    else entry_date.strftime("%Y-%m-%d")
                )

            # Calculate days gap from entry/due date to today
            if due_date_str != "-":
                start_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                dues_days = (datetime.now().date() - start_dt).days
            else:
                dues_days = 0

        new_id = (
            st.session_state.ledger["ID"].max() + 1
            if not st.session_state.ledger.empty
            else 1
        )

        new_entry = {
            "ID": new_id,
            "Date": entry_date.strftime("%d-%b-%Y"),
            "Outlet Name": outlet_name.strip(),
            "Manager": manager,
            "Udhari (Debit)": float(debit),
            "Payment (Credit)": float(credit),
            "Balance": float(current_balance),
            "Due Date": due_date_str,
            "Dues Days": int(dues_days),
        }

        st.session_state.ledger = pd.concat(
            [st.session_state.ledger, pd.DataFrame([new_entry])],
            ignore_index=True,
        )
        st.sidebar.success("Entry Saved Successfully!")
        st.rerun()

# ------------------------------------------------------------------------------
# 4. FILTERS & METRICS
# ------------------------------------------------------------------------------
st.subheader("🔍 लेजर और उधारी फ़िल्टर (Filters)")

col1, col2 = st.columns(2)
with col1:
    outlet_list = ["All Outlets"] + sorted(
        list(st.session_state.ledger["Outlet Name"].unique())
    )
    filter_outlet = st.selectbox("Outlet Wise", outlet_list)
with col2:
    mgr_list = ["All Managers"] + sorted(
        list(st.session_state.ledger["Manager"].unique())
    )
    filter_mgr = st.selectbox("Manager Wise", mgr_list)

# Execute Filters
df_display = st.session_state.ledger.copy()
if filter_outlet != "All Outlets":
    df_display = df_display[df_display["Outlet Name"] == filter_outlet]
if filter_mgr != "All Managers":
    df_display = df_display[df_display["Manager"] == filter_mgr]

# Summary Dashboard
total_debit = (
    df_display["Udhari (Debit)"].sum() if not df_display.empty else 0.0
)
total_credit = (
    df_display["Payment (Credit)"].sum() if not df_display.empty else 0.0
)
total_dues = total_debit - total_credit

m1, m2, m3 = st.columns(3)
m1.metric("कुल उधारी (Total Debit)", f"₹ {total_debit:,.2f}")
m2.metric("कुल जमा (Total Paid)", f"₹ {total_credit:,.2f}")
m3.metric("🔴 कुल बकाया (Net Dues)", f"₹ {total_dues:,.2f}")

# ------------------------------------------------------------------------------
# 5. RECORDS & DELETION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 उधारी और पेमेंट रिकॉर्ड (Ledger Records)")

if df_display.empty:
    st.info("कोई रिकॉर्ड नहीं मिला।")
else:
    # High Performance Dataframe Display
    st.dataframe(
        df_display[
            [
                "ID",
                "Date",
                "Outlet Name",
                "Manager",
                "Udhari (Debit)",
                "Payment (Credit)",
                "Balance",
                "Dues Days",
            ]
        ],
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", format="%d"),
            "Udhari (Debit)": st.column_config.NumberColumn(
                "Udhari (Debit)", format="₹ %.2f"
            ),
            "Payment (Credit)": st.column_config.NumberColumn(
                "Payment (Credit)", format="₹ %.2f"
            ),
            "Balance": st.column_config.NumberColumn(
                "Balance", format="₹ %.2f"
            ),
            "Dues Days": st.column_config.NumberColumn(
                "Dues (Days)", format="%d Days"
            ),
        },
        hide_index=True,
    )

    # Deletion Panel
    with st.expander("🗑️ Entry Deletion Option"):
        del_id = st.number_input(
            "Enter ID to delete record:", min_value=1, step=1
        )
        if st.button("Delete Selected ID"):
            if del_id in st.session_state.ledger["ID"].values:
                st.session_state.ledger = st.session_state.ledger[
                    st.session_state.ledger["ID"] != del_id
                ].reset_index(drop=True)
                st.success(f"Record #{del_id} deleted successfully!")
                st.rerun()
            else:
                st.error("Invalid Entry ID")

# ------------------------------------------------------------------------------
# 6. EXPORT & WHATSAPP
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📄 PDF स्टेटमेंट और WhatsApp शेयरिंग")

col_pdf1, col_pdf2 = st.columns(2)

with col_pdf1:
    if not df_display.empty:
        pdf_file = generate_pdf(df_display, total_dues)
        st.download_button(
            label="📥 Download PDF Statement",
            data=pdf_file,
            file_name=f"CocaCola_Statement_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.write("PDF जनरेट करने के लिए डेटा उपलब्ध नहीं है।")

with col_pdf2:
    whatsapp_num = st.text_input(
        "WhatsApp (Format: 919876543210)", placeholder="91XXXXXXXXXX"
    )
    if st.button("WhatsApp Message Link Generate करें", use_container_width=True):
        if whatsapp_num.strip():
            # Get max Dues Days for context in WhatsApp Message
            max_days = (
                df_display["Dues Days"].max() if not df_display.empty else 0
            )
            msg = f"नमस्ते, Coca-Cola Distribution के अनुसार आपका कुल बकाया हिसाब (Total Dues) ₹ {total_dues:,.2f} है। (पुराना बकाया: {max_days} दिनों से)"
            encoded_msg = pd.Series([msg]).str.replace(" ", "%20").values[0]
            whatsapp_url = (
                f"https://api.whatsapp.com/send?phone={whatsapp_num}&text={encoded_msg}"
            )
            st.markdown(f"[👉 Click Here to Send Message]({whatsapp_url})")
        else:
            st.warning("कृपया मान्य व्हाट्सएप नंबर दर्ज करें!")
