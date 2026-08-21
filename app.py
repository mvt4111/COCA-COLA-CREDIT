import io
from datetime import datetime
import urllib.parse
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# Page Configuration - Mobile Friendly & Scannable
st.set_page_config(
    page_title="MAA VINDHYAWASINI TRADERS(COCA-COLA)",
    page_icon="📕",
    layout="wide",
)

# Custom Styling to mimic Khatabook Red & Green Theme
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

st.title("📕 Digital Khatabook App")
st.caption(
    "Manage sales managers, outlets/customers, debit/credit entries, and export reports"
)

# ------------------------------------------------------------------------------
# 1. STATE MANAGEMENT
# ------------------------------------------------------------------------------
if "ledger" not in st.session_state:
    st.session_state.ledger = pd.DataFrame(
        columns=[
            "ID",
            "Date",
            "Manager Name",
            "Outlet Name",
            "Type",
            "Debit (You Gave)",
            "Credit (You Got)",
            "Balance",
            "Note",
        ]
    )

if "outlets_list" not in st.session_state:
    st.session_state.outlets_list = []

if "managers_list" not in st.session_state:
    st.session_state.managers_list = ["Default Manager"]

if "outlet_manager_map" not in st.session_state:
    st.session_state.outlet_manager_map = {}


def save_manager_name(mgr_str: str) -> str:
    clean_mgr = mgr_str.strip().title()
    if clean_mgr and clean_mgr not in st.session_state.managers_list:
        st.session_state.managers_list.append(clean_mgr)
        st.session_state.managers_list.sort()
    return clean_mgr


def save_outlet_name(outlet_str: str, manager_str: str) -> str:
    clean_outlet = outlet_str.strip().title()
    if clean_outlet:
        if clean_outlet not in st.session_state.outlets_list:
            st.session_state.outlets_list.append(clean_outlet)
            st.session_state.outlets_list.sort()
        st.session_state.outlet_manager_map[clean_outlet] = manager_str
    return clean_outlet


# Function to generate PDF Report
def generate_pdf_report(
    df_data, report_title="Khatabook Statement", subtitle_info=""
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=15,
    )
    table_hdr_style = ParagraphStyle(
        "TableHdr",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.whitesmoke,
        fontName="Helvetica-Bold",
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#334155"),
    )

    elements.append(Paragraph(f"📕 {report_title}", title_style))
    elements.append(
        Paragraph(
            f"{subtitle_info} | Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            sub_style,
        )
    )
    elements.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#0284C7"),
            spaceAfter=15,
        )
    )

    # Summary Card Block inside PDF
    total_given = df_data["Debit (You Gave)"].sum()
    total_got = df_data["Credit (You Got)"].sum()
    total_due = total_given - total_got

    summary_data = [
        [
            Paragraph(
                f"<b>Total Given:</b> Rs {total_given:,.2f}", table_cell_style
            ),
            Paragraph(
                f"<b>Total Got:</b> Rs {total_got:,.2f}", table_cell_style
            ),
            Paragraph(
                f"<b>Net Due Balance:</b> Rs {total_due:,.2f}",
                ParagraphStyle(
                    "DueStyle",
                    parent=table_cell_style,
                    textColor=colors.HexColor("#DC2626"),
                    fontName="Helvetica-Bold",
                ),
            ),
        ]
    ]
    sum_table = Table(summary_data, colWidths=[170, 170, 190])
    sum_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(sum_table)
    elements.append(Spacer(1, 15))

    # Data Table Setup
    headers = [
        "Date",
        "Manager",
        "Outlet",
        "Type / Note",
        "You Gave (Rs)",
        "You Got (Rs)",
        "Balance (Rs)",
    ]
    table_data = [[Paragraph(h, table_hdr_style) for h in headers]]

    for _, row in df_data.iterrows():
        note_str = f"{row['Type']} - {row['Note']}"
        table_data.append(
            [
                Paragraph(str(row["Date"]), table_cell_style),
                Paragraph(str(row["Manager Name"]), table_cell_style),
                Paragraph(str(row["Outlet Name"]), table_cell_style),
                Paragraph(note_str, table_cell_style),
                Paragraph(
                    f"{row['Debit (You Gave)']:,.2f}", table_cell_style
                ),
                Paragraph(
                    f"{row['Credit (You Got)']:,.2f}", table_cell_style
                ),
                Paragraph(f"{row['Balance']:,.2f}", table_cell_style),
            ]
        )

    t = Table(table_data, colWidths=[65, 80, 95, 120, 55, 55, 60])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# Sidebar: Data Backup & Manager/Outlet Management
with st.sidebar:
    st.header("⚙️ Master Settings")

    with st.expander("👤 Manager & Outlet Setup"):
        new_mgr = st.text_input("Add New Sales Manager")
        if st.button("Save Manager"):
            if new_mgr.strip():
                save_manager_name(new_mgr)
                st.success(f"Added Manager: {new_mgr}")
                st.rerun()

        st.divider()
        st.write("**Current Managers:**")
        st.write(", ".join(st.session_state.managers_list))

    with st.expander("💾 Data Backup & Restore"):
        uploaded_file = st.file_uploader("Upload Backup CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                if "Manager Name" not in uploaded_df.columns:
                    uploaded_df["Manager Name"] = "Default Manager"
                st.session_state.ledger = uploaded_df
                st.session_state.outlets_list = sorted(
                    list(
                        st.session_state.ledger["Outlet Name"]
                        .dropna()
                        .unique()
                    )
                )
                st.session_state.managers_list = sorted(
                    list(
                        st.session_state.ledger["Manager Name"]
                        .dropna()
                        .unique()
                    )
                )
                st.success("Ledger data restored successfully!")
            except Exception as e:
                st.error(f"Error loading file: {e}")

        if not st.session_state.ledger.empty:
            csv_buf = st.session_state.ledger.to_csv(index=False).encode(
                "utf-8"
            )
            st.download_button(
                label="📥 Download Full Backup (CSV)",
                data=csv_buf,
                file_name=f"khatabook_backup_{datetime.now().strftime('%d-%m-%Y')}.csv",
                mime="text/csv",
            )

# ------------------------------------------------------------------------------
# 2. KHATABOOK ENTRY SECTION (Manager & Outlet Wise)
# ------------------------------------------------------------------------------
st.markdown("---")

col_left, col_right = st.columns(2)

# 🔴 RED SECTION: You Gave (Debit / Credit Given)
with col_left:
    st.markdown(
        """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">🔴 YOU GAVE (Debit / Credit)</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record debit entry assigned by Manager to Outlet</p>
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
            u_outlet = st.text_input(
                "Enter New Store Name", key="u_outlet_text"
            )
        else:
            u_outlet = selected_u_outlet

        u_amount = st.number_input(
            "Amount (Rs)", min_value=0.0, step=50.0, key="u_amt"
        )
        u_note = st.text_input("Details / Bill Notes (Optional)", key="u_note")

        btn_udhari = st.form_submit_button("🔴 Save Entry (You Gave)")

    if btn_udhari:
        if not u_outlet.strip():
            st.error("Please enter a valid Outlet Name!")
        elif u_amount <= 0:
            st.error("Please enter a valid amount greater than zero!")
        else:
            final_outlet = save_outlet_name(u_outlet, u_manager)
            formatted_date = u_date.strftime("%d-%m-%Y")

            outlet_df = st.session_state.ledger[
                st.session_state.ledger["Outlet Name"] == final_outlet
            ]
            prev_balance = (
                outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0.0
            )
            new_balance = prev_balance + u_amount

            new_id = (
                int(st.session_state.ledger["ID"].max()) + 1
                if not st.session_state.ledger.empty
                else 1
            )

            entry = {
                "ID": new_id,
                "Date": formatted_date,
                "Manager Name": u_manager,
                "Outlet Name": final_outlet,
                "Type": "🔴 You Gave",
                "Debit (You Gave)": float(u_amount),
                "Credit (You Got)": 0.0,
                "Balance": float(new_balance),
                "Note": u_note if u_note else "Credit Bill",
            }

            st.session_state.ledger = pd.concat(
                [st.session_state.ledger, pd.DataFrame([entry])],
                ignore_index=True,
            )
            st.success(
                f"🔴 Added Rs {u_amount:,.2f} credit entry for {final_outlet} (Mgr: {u_manager})"
            )
            st.rerun()

# 🟢 GREEN SECTION: You Got (Credit / Payment Received)
with col_right:
    st.markdown(
        """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">🟢 YOU GOT (Credit / Payment)</h3>
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
                "Date",
                datetime.now(),
                format="DD/MM/YYYY",
                key="p_date_key",
            )
            p_outlet = st.selectbox(
                "Select Customer / Outlet",
                st.session_state.outlets_list,
                key="p_outlet_select",
            )

            # Auto-detect associated manager
            default_mgr = st.session_state.outlet_manager_map.get(
                p_outlet, st.session_state.managers_list[0]
            )
            p_manager = st.selectbox(
                "Sales Manager",
                st.session_state.managers_list,
                index=st.session_state.managers_list.index(default_mgr)
                if default_mgr in st.session_state.managers_list
                else 0,
                key="p_mgr_select",
            )

            p_outlet_df = st.session_state.ledger[
                st.session_state.ledger["Outlet Name"] == p_outlet
            ]
            current_due = (
                p_outlet_df["Balance"].iloc[-1]
                if not p_outlet_df.empty
                else 0.0
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

            btn_payment = st.form_submit_button("🟢 Save Payment (You Got)")

        if btn_payment:
            if p_amount <= 0:
                st.error("Please enter a valid amount greater than zero!")
            else:
                formatted_date = p_date.strftime("%d-%m-%Y")
                new_balance = current_due - p_amount

                new_id = (
                    int(st.session_state.ledger["ID"].max()) + 1
                    if not st.session_state.ledger.empty
                    else 1
                )

                entry = {
                    "ID": new_id,
                    "Date": formatted_date,
                    "Manager Name": p_manager,
                    "Outlet Name": p_outlet,
                    "Type": "🟢 You Got",
                    "Debit (You Gave)": 0.0,
                    "Credit (You Got)": float(p_amount),
                    "Balance": float(new_balance),
                    "Note": f"Payment ({p_mode})",
                }

                st.session_state.ledger = pd.concat(
                    [st.session_state.ledger, pd.DataFrame([entry])],
                    ignore_index=True,
                )
                st.success(
                    f"🟢 Received Rs {p_amount:,.2f} payment from {p_outlet}"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# 3. MANAGER & OUTLET FILTERED DASHBOARD + PDF & WHATSAPP EXPORTS
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Manager & Outlet Wise Ledger Dashboard")

if st.session_state.ledger.empty:
    st.info("No ledger records available to display.")
else:
    f_col1, f_col2 = st.columns(2)

    with f_col1:
        selected_mgr_filter = st.selectbox(
            "Filter by Manager:",
            options=["All Managers"] + st.session_state.managers_list,
        )

    # Filter outlets based on selected manager
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

    # Apply Filtering Logic
    df_view = st.session_state.ledger.copy()
    if selected_mgr_filter != "All Managers":
        df_view = df_view[df_view["Manager Name"] == selected_mgr_filter]

    if selected_outlet_filter != "All Outlets":
        df_view = df_view[df_view["Outlet Name"] == selected_outlet_filter]

    # Metrics Summary
    tot_given = df_view["Debit (You Gave)"].sum()
    tot_got = df_view["Credit (You Got)"].sum()
    tot_due = tot_given - tot_got

    m1, m2, m3 = st.columns(3)
    m1.metric("Total You Gave", f"Rs {tot_given:,.2f}")
    m2.metric("Total You Got", f"Rs {tot_got:,.2f}")
    m3.metric("🔴 Net Outstanding Due", f"Rs {tot_due:,.2f}")

    # Ledger Table Display
    st.dataframe(
        df_view[
            [
                "ID",
                "Date",
                "Manager Name",
                "Outlet Name",
                "Note",
                "Debit (You Gave)",
                "Credit (You Got)",
                "Balance",
            ]
        ],
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", format="%d"),
            "Date": st.column_config.TextColumn("Date (DD-MM-YYYY)"),
            "Manager Name": st.column_config.TextColumn("Manager"),
            "Outlet Name": st.column_config.TextColumn("Outlet"),
            "Debit (You Gave)": st.column_config.NumberColumn(
                "🔴 You Gave (Rs)", format="Rs %.2f"
            ),
            "Credit (You Got)": st.column_config.NumberColumn(
                "🟢 You Got (Rs)", format="Rs %.2f"
            ),
            "Balance": st.column_config.NumberColumn(
                "Balance Due (Rs)", format="Rs %.2f"
            ),
        },
        hide_index=True,
    )

    # --------------------------------------------------------------------------
    # EXPORT OPTIONS: PDF & WHATSAPP
    # --------------------------------------------------------------------------
    st.markdown("### 📄 Export & WhatsApp Sharing Options")

    exp_col1, exp_col2 = st.columns(2)

    # 1. PDF Export
    with exp_col1:
        st.write("#### 📑 PDF Statement Export")
        rep_title = f"Ledger Report - {selected_outlet_filter}"
        rep_sub = f"Manager: {selected_mgr_filter} | Outlet: {selected_outlet_filter}"

        pdf_bytes = generate_pdf_report(
            df_view, report_title=rep_title, subtitle_info=rep_sub
        )

        st.download_button(
            label="📄 Download PDF Ledger Statement",
            data=pdf_bytes,
            file_name=f"Khatabook_{selected_mgr_filter}_{selected_outlet_filter}_{datetime.now().strftime('%d%m%Y')}.pdf",
            mime="application/pdf",
        )

    # 2. WhatsApp Export
    with exp_col2:
        st.write("#### 💬 WhatsApp Direct Statement Export")
        wa_phone = st.text_input(
            "Customer / Manager WhatsApp Number", placeholder="91XXXXXXXXXX"
        )

        if st.button("📲 Generate WhatsApp Summary Link"):
            if wa_phone.strip():
                # Format summary text for WhatsApp
                wa_text = f"*📕 KHATABOOK STATEMENT*\n"
                wa_text += f"*Manager:* {selected_mgr_filter}\n"
                wa_text += f"*Outlet:* {selected_outlet_filter}\n"
                wa_text += f"*Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
                wa_text += f"-----------------------------------\n"
                wa_text += f"🔴 *Total Given:* Rs {tot_given:,.2f}\n"
                wa_text += f"🟢 *Total Got:* Rs {tot_got:,.2f}\n"
                wa_text += f"📌 *NET BALANCE DUE:* Rs {tot_due:,.2f}\n"
                wa_text += f"-----------------------------------\n"
                wa_text += (
                    "Please arrange the payment at the earliest. Thank you!"
                )

                encoded_text = urllib.parse.quote(wa_text)
                wa_url = f"https://api.whatsapp.com/send?phone={wa_phone.strip()}&text={encoded_text}"

                st.markdown(
                    f"[👉 Click Here to Send Statement via WhatsApp]({wa_url})"
                )
            else:
                st.warning("Please enter a valid WhatsApp phone number!")
