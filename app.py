import io
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Coca-Cola Credit Tracker", page_icon="🥤", layout="wide"
)

# Custom CSS for UI Enhancement
st.markdown(
    """
    <style>
    /* Styling for clear readability */
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stDateInput label {
        font-weight: bold !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🥤 Coca-Cola Distribution - Credit & Ledger App")
st.caption(
    "500+ Outlets, Manager & Mode-Wise Ledger with Auto Outlet Saving & Visual Entry"
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
            f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
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

    col_widths = [25, 65, 115, 85, 55, 65, 65, 65, 42]
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
# 2. STATE MANAGEMENT & AUTO OUTLET SAVING
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

# Master Outlets List Initialization
if "outlets_list" not in st.session_state:
    st.session_state.outlets_list = []

# Sidebar: CSV Import/Export
with st.sidebar.expander("💾 Backup & Restore Data"):
    uploaded_file = st.file_uploader("Restore Ledger CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            st.session_state.ledger = pd.read_csv(uploaded_file)
            st.session_state.outlets_list = sorted(
                list(st.session_state.ledger["Outlet Name"].dropna().unique())
            )
            st.success("Ledger restored successfully!")
        except Exception as e:
            st.error(f"Error loading CSV: {e}")

    if not st.session_state.ledger.empty:
        csv_buffer = st.session_state.ledger.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Data (CSV)",
            data=csv_buffer,
            file_name=f"ledger_backup_{datetime.now().strftime('%d-%m-%Y')}.csv",
            mime="text/csv",
        )


# Helper function to auto-save and update master outlet list
def save_outlet_name(name_str: str) -> str:
    clean_name = name_str.strip().title()
    if clean_name and clean_name not in st.session_state.outlets_list:
        st.session_state.outlets_list.append(clean_name)
        st.session_state.outlets_list.sort()
    return clean_name


# ------------------------------------------------------------------------------
# 3. RED & GREEN ENTRY TABS (EASY VISUAL ENTRY)
# ------------------------------------------------------------------------------
st.markdown("### 📝 एंट्री दर्ज करें (Quick Entry Panel)")

entry_tab1, entry_tab2 = st.tabs([
    "🔴 नई उधारी बिल दर्ज करें (New Debit Entry)",
    "🟢 पेमेंट जमा दर्ज करें (Credit / Part Payment Entry)",
])

# 🔴 RED TAB - DEBIT / UDHARI ENTRY
with entry_tab1:
    st.error("🔴 **उधारी (Debit) बिल की प्रविष्टि करें**")
    with st.form(key="debit_form", clear_on_submit=True):
        col_d1, col_d2 = st.columns(2)

        with col_d1:
            d_date = st.date_input(
                "Entry Date (तारीख)", datetime.now(), format="DD/MM/YYYY"
            )

            # Outlet Selection or Custom Input
            existing_outlets = [
                "+ Naya Outlet Add Karen"
            ] + st.session_state.outlets_list
            selected_outlet_d = st.selectbox(
                "Outlet का नाम चुनें (या नया जोड़ें)",
                existing_outlets,
                key="d_out_select",
            )

            if selected_outlet_d == "+ Naya Outlet Add Karen":
                d_outlet = st.text_input(
                    "नए दुकान/आउटलेट का नाम दर्ज करें", key="d_out_text"
                )
            else:
                d_outlet = selected_outlet_d

        with col_d2:
            d_manager = st.selectbox(
                "Assigned Manager",
                ["PIYUSH YADAV", "RUKSHAT ALAM", "SUMIT MGR", "PRAKASH MGR"],
                key="d_mgr_select",
            )
            d_amount = st.number_input(
                "उधारी बिल राशि (₹)",
                min_value=0.0,
                step=100.0,
                key="d_amt_input",
            )

        submit_debit = st.form_submit_button("🔴 Udhari Save Karen")

    if submit_debit:
        if not d_outlet.strip():
            st.error("कृपया आउटलेट का नाम दर्ज करें!")
        elif d_amount <= 0:
            st.error("कृपया वैध उधारी राशि दर्ज करें!")
        else:
            final_outlet = save_outlet_name(d_outlet)
            formatted_date_str = d_date.strftime("%d-%m-%Y")

            outlet_df = st.session_state.ledger[
                st.session_state.ledger["Outlet Name"] == final_outlet
            ]
            prev_balance = (
                outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0.0
            )
            current_balance = prev_balance + d_amount

            # Calculate Dues Days
            due_date_str = d_date.strftime("%Y-%m-%d")
            start_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            dues_days = (datetime.now().date() - start_dt).days

            new_id = (
                int(st.session_state.ledger["ID"].max()) + 1
                if not st.session_state.ledger.empty
                else 1
            )

            new_entry = {
                "ID": new_id,
                "Date": formatted_date_str,
                "Outlet Name": final_outlet,
                "Manager": d_manager,
                "Payment Mode": "N/A (Udhari)",
                "Udhari (Debit)": float(d_amount),
                "Payment (Credit)": 0.0,
                "Balance": float(current_balance),
                "Due Date": due_date_str,
                "Dues Days": int(dues_days),
            }

            st.session_state.ledger = pd.concat(
                [st.session_state.ledger, pd.DataFrame([new_entry])],
                ignore_index=True,
            )
            st.success(
                f"🔴 ₹ {d_amount:,.2f} Udhari Entry Recorded for {final_outlet}!"
            )
            st.rerun()


# 🟢 GREEN TAB - CREDIT / PAYMENT RECEIVED ENTRY
with entry_tab2:
    st.success("🟢 **पेमेंट जमा / किश्त (Credit Entry) की प्रविष्टि करें**")

    if not st.session_state.outlets_list:
        st.info("अभी कोई आउटलेट पंजीकृत नहीं है। पहले उधारी एंट्री दर्ज करें।")
    else:
        with st.form(key="credit_form", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                c_date = st.date_input(
                    "Payment Date (तारीख)", datetime.now(), format="DD/MM/YYYY"
                )
                c_outlet = st.selectbox(
                    "Outlet चुनें",
                    st.session_state.outlets_list,
                    key="c_out_select",
                )

                # Get current balance for selected outlet
                c_outlet_df = st.session_state.ledger[
                    st.session_state.ledger["Outlet Name"] == c_outlet
                ]
                c_curr_due = (
                    c_outlet_df["Balance"].iloc[-1]
                    if not c_outlet_df.empty
                    else 0.0
                )
                c_outlet_mgr = (
                    c_outlet_df["Manager"].iloc[-1]
                    if not c_outlet_df.empty
                    else "PIYUSH YADAV"
                )

                st.info(f"👉 **{c_outlet} का कुल बकाया:** ₹ {c_curr_due:,.2f}")

            with col_c2:
                c_amount = st.number_input(
                    "जमा राशि (Payment Amount ₹)",
                    min_value=0.0,
                    step=100.0,
                    key="c_amt_input",
                )
                c_mode = st.selectbox(
                    "Payment Mode (भुगतान का प्रकार)",
                    [
                        "Cash",
                        "Online (UPI/GPay/PhonePe)",
                        "Bank Transfer (NEFT/RTGS)",
                        "Cheque",
                    ],
                    key="c_mode_select",
                )

                mgr_options = [
                    "PIYUSH YADAV",
                    "RUKSHAT ALAM",
                    "SUMIT MGR",
                    "PRAKASH MGR",
                ]
                mgr_idx = (
                    mgr_options.index(c_outlet_mgr)
                    if c_outlet_mgr in mgr_options
                    else 0
                )
                c_manager = st.selectbox(
                    "Assigned Manager",
                    mgr_options,
                    index=mgr_idx,
                    key="c_mgr_select",
                )

            submit_credit = st.form_submit_button("🟢 Payment Jama Karen")

        if submit_credit:
            if c_amount <= 0:
                st.error("कृपया वैध जमा राशि दर्ज करें!")
            else:
                formatted_date_str = c_date.strftime("%d-%m-%Y")
                new_bal = c_curr_due - c_amount

                if new_bal <= 0:
                    due_dt_str = "-"
                    d_days = 0
                else:
                    due_dt_str = (
                        c_outlet_df["Due Date"].iloc[-1]
                        if not c_outlet_df.empty
                        and "Due Date" in c_outlet_df.columns
                        else c_date.strftime("%Y-%m-%d")
                    )
                    if due_dt_str != "-":
                        start_dt = datetime.strptime(
                            due_dt_str, "%Y-%m-%d"
                        ).date()
                        d_days = (datetime.now().date() - start_dt).days
                    else:
                        d_days = 0

                new_id = (
                    int(st.session_state.ledger["ID"].max()) + 1
                    if not st.session_state.ledger.empty
                    else 1
                )

                credit_entry = {
                    "ID": new_id,
                    "Date": formatted_date_str,
                    "Outlet Name": c_outlet,
                    "Manager": c_manager,
                    "Payment Mode": c_mode,
                    "Udhari (Debit)": 0.0,
                    "Payment (Credit)": float(c_amount),
                    "Balance": float(new_bal),
                    "Due Date": due_dt_str,
                    "Dues Days": int(d_days),
                }

                st.session_state.ledger = pd.concat(
                    [st.session_state.ledger, pd.DataFrame([credit_entry])],
                    ignore_index=True,
                )
                st.success(
                    f"🟢 ₹ {c_amount:,.2f} ({c_mode}) Payment Jama Successfully for {c_outlet}!"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# 4. FILTERS & METRICS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔍 लेजर फ़िल्टर (Search & Filter)")

col1, col2, col3 = st.columns(3)
with col1:
    outlet_list = ["All Outlets"] + st.session_state.outlets_list
    filter_outlet = st.selectbox("Outlet Wise", outlet_list)
with col2:
    mgr_list = ["All Managers"] + sorted(
        list(st.session_state.ledger["Manager"].dropna().unique())
    )
    filter_mgr = st.selectbox("Manager Wise", mgr_list)
with col3:
    mode_list = ["All Modes"] + sorted(
        list(st.session_state.ledger["Payment Mode"].dropna().unique())
    )
    filter_mode = st.selectbox("Payment Mode Wise", mode_list)

# Filter Logic
df_display = st.session_state.ledger.copy()
if filter_outlet != "All Outlets":
    df_display = df_display[df_display["Outlet Name"] == filter_outlet]
if filter_mgr != "All Managers":
    df_display = df_display[df_display["Manager"] == filter_mgr]
if filter_mode != "All Modes":
    df_display = df_display[df_display["Payment Mode"] == filter_mode]

# Summary Dashboard Metrics
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
# 5. RECORDS TABLE & DELETION
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 लेजर रिकॉर्ड्स टेबल")

if df_display.empty:
    st.info("कोई रिकॉर्ड उपलब्ध नहीं है।")
else:
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
            "Date": st.column_config.TextColumn("Date (DD-MM-YYYY)"),
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

    with st.expander("🗑️ Entry Delete Karen (गलत एंट्री हटाएं)"):
        del_id = st.number_input(
            "Enter Entry ID to delete:", min_value=1, step=1
        )
        if st.button("Delete Selected ID"):
            if del_id in st.session_state.ledger["ID"].values:
                st.session_state.ledger = st.session_state.ledger[
                    st.session_state.ledger["ID"] != del_id
                ].reset_index(drop=True)
                st.session_state.outlets_list = sorted(
                    list(
                        st.session_state.ledger["Outlet Name"].dropna().unique()
                    )
                )
                st.success(f"Record #{del_id} deleted successfully!")
                st.rerun()
            else:
                st.error("अमान्य ID! कृपया सही ID दर्ज करें।")

# ------------------------------------------------------------------------------
# 6. PDF EXPORT OPTIONS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📄 PDF रिपोर्ट एक्सपोर्ट")

pdf_tab1, pdf_tab2, pdf_tab3 = st.tabs([
    "🏪 Outlet Wise PDF",
    "👨‍💼 Manager Wise PDF",
    "📊 Current View PDF",
])

# Tab 1: Outlet-wise PDF Report
with pdf_tab1:
    selected_outlet_pdf = st.selectbox(
        "Select Outlet for PDF",
        options=st.session_state.outlets_list,
        key="pdf_outlet_select",
    )
    if selected_outlet_pdf:
        df_outlet_pdf = st.session_state.ledger[
            st.session_state.ledger["Outlet Name"] == selected_outlet_pdf
        ]
        outlet_dues = (
            df_outlet_pdf["Udhari (Debit)"].sum()
            - df_outlet_pdf["Payment (Credit)"].sum()
        )

        pdf_outlet_file = generate_pdf(
            df_outlet_pdf,
            title_suffix=f"- Outlet: {selected_outlet_pdf}",
            total_dues_amount=outlet_dues,
        )
        st.download_button(
            label=f"📥 Download Statement for {selected_outlet_pdf}",
            data=pdf_outlet_file,
            file_name=f"Statement_Outlet_{selected_outlet_pdf.replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# Tab 2: Manager-wise PDF Report
with pdf_tab2:
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
                file_name=f"Statement_Manager_{selected_manager.replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info(f"{selected_manager} के लिए कोई डेटा उपलब्ध नहीं है।")

# Tab 3: Current Filtered View PDF Report
with pdf_tab3:
    if not df_display.empty:
        pdf_current_file = generate_pdf(
            df_display,
            title_suffix="- Filtered View",
            total_dues_amount=total_dues,
        )
        st.download_button(
            label="📥 Download Current View PDF Statement",
            data=pdf_current_file,
            file_name=f"Statement_Filtered_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("डाउनलोड करने के लिए डेटा उपलब्ध नहीं है।")

# ------------------------------------------------------------------------------
# 7. WHATSAPP SHARING SECTION
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
