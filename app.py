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
st.caption(
    "500+ Outlets, Manager & Mode-Wise Ledger with Part Payment Support"
)


# ------------------------------------------------------------------------------
# 1. HELPER FUNCTIONS FOR PDF GENERATION
# ------------------------------------------------------------------------------
def generate_pdf(
    dataframe: pd.DataFrame,
    title_suffix: str = "",
    total_dues_amount: float = 0.0,
) -> io.BytesIO:
    """Generates a styled PDF report statement using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=15,
        leftMargin=15,
        topMargin=25,
        bottomMargin=25,
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=15,
        leading=18,
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
            f"<b>Coca-Cola Distribution - Statement {title_suffix}</b>",
            title_style,
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
    elements.append(Spacer(1, 10))

    # Table Setup
    headers = [
        "ID",
        "Date",
        "Outlet Name",
        "Manager",
        "Mode",
        "Debit (₹)",
        "Credit (₹)",
        "Balance (₹)",
        "Dues Days",
    ]
    table_data = [[Paragraph(h, header_style) for h in headers]]

    for _, row in dataframe.iterrows():
        table_data.append([
            Paragraph(str(row["ID"]), cell_style),
            Paragraph(str(row["Date"]), cell_style),
            Paragraph(str(row["Outlet Name"]), cell_style),
            Paragraph(str(row["Manager"]), cell_style),
            Paragraph(str(row["Payment Mode"]), cell_style),
            Paragraph(f"{row['Udhari (Debit)']:,.2f}", cell_style),
            Paragraph(f"{row['Payment (Credit)']:,.2f}", cell_style),
            Paragraph(f"{row['Balance']:,.2f}", cell_style),
            Paragraph(str(row["Dues Days"]), cell_style),
        ])

    # Dynamic Column Widths
    col_widths = [25, 60, 115, 85, 55, 65, 65, 65, 47]
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
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
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
            "Payment Mode",
            "Udhari (Debit)",
            "Payment (Credit)",
            "Balance",
            "Due Date",
            "Dues Days",
        ]
    )

# Sidebar: CSV Import/Export
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
# 3. SIDEBAR FORM ENTRY (NEW BILL / CREDIT ENTRY)
# ------------------------------------------------------------------------------
st.sidebar.header("➕ नई बिल / उधारी एंट्री (New Entry)")

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
    payment_mode = st.selectbox(
        "Payment Mode (भुगतान का प्रकार)",
        ["Cash", "Online (UPI/GPay/PhonePe)", "Bank Transfer (NEFT/RTGS)", "Cheque", "N/A (Udhari)"],
    )
    amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)

    submit_button = st.form_submit_button("Save Entry (रजिस्टर करें)")

if submit_button:
    if not outlet_name.strip():
        st.sidebar.error("कृपया आउटलेट का नाम दर्ज करें!")
    else:
        debit = amount if trans_type == "Udhari (Debit)" else 0.0
        credit = amount if trans_type == "Payment Received (Credit)" else 0.0

        outlet_df = st.session_state.ledger[
            st.session_state.ledger["Outlet Name"] == outlet_name.strip()
        ]
        prev_balance = (
            outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0.0
        )
        current_balance = prev_balance + debit - credit

        # Calculate Dues Days
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
            "Payment Mode": payment_mode if trans_type == "Payment Received (Credit)" else "N/A",
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
# 4. PART PAYMENT QUICK RECEIPT SECTION
# ------------------------------------------------------------------------------
st.markdown("### 💰 पार्ट पेमेंट प्राप्ति (Part Payment Collector)")
st.info(
    "यदि कोई आउटलेट थोड़ा-थोड़ा (Part Payment) करके पैसा जमा करता है, तो यहाँ से आसानी से दर्ज करें:"
)

existing_outlets = sorted(
    list(st.session_state.ledger["Outlet Name"].unique())
)

if not existing_outlets:
    st.warning("अभी कोई आउटलेट पंजीकृत नहीं है। Sidebar से पहली एंट्री दर्ज करें।")
else:
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    with p_col1:
        part_outlet = st.selectbox(
            "Outlet चुनें", existing_outlets, key="part_outlet_sel"
        )
    
    # Calculate current due balance for selected outlet
    part_df = st.session_state.ledger[
        st.session_state.ledger["Outlet Name"] == part_outlet
    ]
    curr_due = part_df["Balance"].iloc[-1] if not part_df.empty else 0.0
    outlet_mgr = part_df["Manager"].iloc[-1] if not part_df.empty else "PIYUSH YADAV"

    with p_col2:
        st.write(f"**वर्तमान बकाया:** ₹ {curr_due:,.2f}")
        part_amount = st.number_input(
            "जमा राशि (Part Amount ₹)",
            min_value=0.0,
            max_value=float(max(curr_due, 0.0)) if curr_due > 0 else 100000.0,
            step=500.0,
            key="part_amt_input",
        )

    with p_col3:
        part_mode = st.selectbox(
            "Payment Mode",
            ["Cash", "Online (UPI/GPay/PhonePe)", "Bank Transfer (NEFT/RTGS)", "Cheque"],
            key="part_mode_sel",
        )
        part_date = st.date_input(
            "Payment Date", datetime.now(), key="part_dt_input"
        )

    with p_col4:
        st.write("")
        st.write("")
        if st.button("💵 Part Payment जमा करें", use_container_width=True):
            if part_amount <= 0:
                st.error("कृपया 0 से अधिक राशि दर्ज करें!")
            else:
                new_bal = curr_due - part_amount
                
                if new_bal <= 0:
                    due_dt_str = "-"
                    d_days = 0
                else:
                    due_dt_str = (
                        part_df["Due Date"].iloc[-1]
                        if "Due Date" in part_df.columns
                        else part_date.strftime("%Y-%m-%d")
                    )
                    if due_dt_str != "-":
                        start_dt = datetime.strptime(
                            due_dt_str, "%Y-%m-%d"
                        ).date()
                        d_days = (datetime.now().date() - start_dt).days
                    else:
                        d_days = 0

                p_id = (
                    st.session_state.ledger["ID"].max() + 1
                    if not st.session_state.ledger.empty
                    else 1
                )

                part_entry = {
                    "ID": p_id,
                    "Date": part_date.strftime("%d-%b-%Y"),
                    "Outlet Name": part_outlet,
                    "Manager": outlet_mgr,
                    "Payment Mode": part_mode,
                    "Udhari (Debit)": 0.0,
                    "Payment (Credit)": float(part_amount),
                    "Balance": float(new_bal),
                    "Due Date": due_dt_str,
                    "Dues Days": int(d_days),
                }

                st.session_state.ledger = pd.concat(
                    [st.session_state.ledger, pd.DataFrame([part_entry])],
                    ignore_index=True,
                )
                st.success(
                    f"Part Payment ₹ {part_amount:,.2f} ({part_mode}) Safal Recorded for {part_outlet}!"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# 5. FILTERS & METRICS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔍 लेजर और उधारी फ़िल्टर (Filters)")

col1, col2, col3 = st.columns(3)
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
with col3:
    mode_list = ["All Modes"] + sorted(
        list(st.session_state.ledger["Payment Mode"].unique())
    )
    filter_mode = st.selectbox("Payment Mode Wise", mode_list)

# Execute Filters
df_display = st.session_state.ledger.copy()
if filter_outlet != "All Outlets":
    df_display = df_display[df_display["Outlet Name"] == filter_outlet]
if filter_mgr != "All Managers":
    df_display = df_display[df_display["Manager"] == filter_mgr]
if filter_mode != "All Modes":
    df_display = df_display[df_display["Payment Mode"] == filter_mode]

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
# 6. RECORDS TABLE & DELETION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 उधारी और पेमेंट रिकॉर्ड (Ledger Records)")

if df_display.empty:
    st.info("कोई रिकॉर्ड नहीं मिला।")
else:
    # Interactive Dataframe Display
    st.dataframe(
        df_display[
            [
                "ID",
                "Date",
                "Outlet Name",
                "Manager",
                "Payment Mode",
                "Udhari (Debit)",
                "Payment (Credit)",
                "Balance",
                "Dues Days",
            ]
        ],
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", format="%d"),
            "Payment Mode": st.column_config.TextColumn("Mode"),
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
# 7. PDF EXPORT OPTIONS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📄 PDF रिपोर्ट एक्सपोर्ट (Export PDF Reports)")

pdf_tab1, pdf_tab2, pdf_tab3 = st.tabs([
    "🏪 Outlet Wise PDF",
    "👨‍💼 Manager Wise PDF",
    "📊 Current View PDF",
])

# Tab 1: Outlet-wise PDF Report
with pdf_tab1:
    st.write("किसी विशिष्ट Outlet की पार्ट-पेमेंट लेज़र रिपोर्ट PDF डाउनलोड करें:")
    selected_outlet = st.selectbox(
        "Select Outlet for PDF",
        options=sorted(list(st.session_state.ledger["Outlet Name"].unique())),
        key="pdf_outlet_select",
    )
    if selected_outlet:
        df_outlet_pdf = st.session_state.ledger[
            st.session_state.ledger["Outlet Name"] == selected_outlet
        ]
        outlet_dues = (
            df_outlet_pdf["Udhari (Debit)"].sum()
            - df_outlet_pdf["Payment (Credit)"].sum()
        )

        pdf_outlet_file = generate_pdf(
            df_outlet_pdf,
            title_suffix=f"- Outlet: {selected_outlet}",
            total_dues_amount=outlet_dues,
        )
        st.download_button(
            label=f"📥 Download Statement for {selected_outlet}",
            data=pdf_outlet_file,
            file_name=f"Statement_Outlet_{selected_outlet.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# Tab 2: Manager-wise PDF Report
with pdf_tab2:
    st.write("किसी Manager के अधीन सभी Outlets की संयुक्त PDF रिपोर्ट:")
    manager_options = ["PIYUSH YADAV", "RUKSHAT ALAM", "SUMIT MGR", "PRAKASH MGR"]
    selected_manager = st.selectbox(
        "Select Manager for PDF",
        options=manager_options,
        key="pdf_manager_select",
    )
    if selected_manager:
        df_mgr_pdf = st.session_state.ledger[
            st.session_state.ledger["Manager"] == selected_manager
        ]
        mgr_dues = (
            df_mgr_pdf["Udhari (Debit)"].sum()
            - df_mgr_pdf["Payment (Credit)"].sum()
            if not df_mgr_pdf.empty
            else 0.0
        )

        if not df_mgr_pdf.empty:
            pdf_mgr_file = generate_pdf(
                df_mgr_pdf,
                title_suffix=f"- Manager: {selected_manager}",
                total_dues_amount=mgr_dues,
            )
            st.download_button(
                label=f"📥 Download Combined PDF for Manager ({selected_manager})",
                data=pdf_mgr_file,
                file_name=f"Statement_Manager_{selected_manager.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info(f"{selected_manager} के लिए कोई डेटा उपलब्ध नहीं है।")

# Tab 3: Current Filtered View PDF Report
with pdf_tab3:
    st.write("वर्तमान फ़िल्टर (Filtered View) की PDF डाउनलोड करें:")
    if not df_display.empty:
        pdf_current_file = generate_pdf(
            df_display,
            title_suffix="- Filtered View",
            total_dues_amount=total_dues,
        )
        st.download_button(
            label="📥 Download Current View PDF Statement",
            data=pdf_current_file,
            file_name=f"Statement_Filtered_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("डाउनलोड करने के लिए डेटा उपलब्ध नहीं है।")

# ------------------------------------------------------------------------------
# 8. WHATSAPP SHARING SECTION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("💬 WhatsApp शेयरिंग")

whatsapp_num = st.text_input(
    "WhatsApp Number (Format: 919876543210)", placeholder="91XXXXXXXXXX"
)
if st.button("WhatsApp Message Link Generate करें", use_container_width=True):
    if whatsapp_num.strip():
        max_days = df_display["Dues Days"].max() if not df_display.empty else 0
        msg = f"नमस्ते, Coca-Cola Distribution के अनुसार आपका कुल बकाया हिसाब (Total Dues) ₹ {total_dues:,.2f} है। (पुराना बकाया: {max_days} दिनों से)"
        encoded_msg = pd.Series([msg]).str.replace(" ", "%20").values[0]
        whatsapp_url = (
            f"https://api.whatsapp.com/send?phone={whatsapp_num}&text={encoded_msg}"
        )
        st.markdown(f"[👉 Click Here to Send Message]({whatsapp_url})")
    else:
        st.warning("कृपया मान्य व्हाट्सएप नंबर दर्ज करें!")
