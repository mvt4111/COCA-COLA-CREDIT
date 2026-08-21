import io
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# Page Configuration - Mobile Friendly & Scannable
st.set_page_config(
    page_title="Digital Khatabook", page_icon="📕", layout="wide"
)

# Custom Styling to mimic Khatabook Red & Green Theme
st.markdown(
    """
    <style>
    /* Card Container Styles */
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
    .khatabook-header {
        font-size: 24px;
        font-weight: bold;
        color: #1E293B;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📕 Digital Khatabook App")
st.caption("Manage customer credit ledgers, entries, and payment collection")

# ------------------------------------------------------------------------------
# 1. STATE MANAGEMENT (Auto Customer/Outlet Saving)
# ------------------------------------------------------------------------------
if "ledger" not in st.session_state:
    st.session_state.ledger = pd.DataFrame(
        columns=[
            "ID",
            "Date",
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


def save_outlet_name(name_str: str) -> str:
    clean_name = name_str.strip().title()
    if clean_name and clean_name not in st.session_state.outlets_list:
        st.session_state.outlets_list.append(clean_name)
        st.session_state.outlets_list.sort()
    return clean_name


# Sidebar: Data Backup & Restore
with st.sidebar.expander("💾 Data Backup & Restore"):
    uploaded_file = st.file_uploader("Upload Backup CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            st.session_state.ledger = pd.read_csv(uploaded_file)
            st.session_state.outlets_list = sorted(
                list(st.session_state.ledger["Outlet Name"].dropna().unique())
            )
            st.success("Ledger data loaded successfully!")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    if not st.session_state.ledger.empty:
        csv_buffer = st.session_state.ledger.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Data Backup (CSV)",
            data=csv_buffer,
            file_name=f"khatabook_backup_{datetime.now().strftime('%d-%m-%Y')}.csv",
            mime="text/csv",
        )

# ------------------------------------------------------------------------------
# 2. KHATABOOK ENTRY SECTION (Red / Green Cards)
# ------------------------------------------------------------------------------
st.markdown("---")

col_left, col_right = st.columns(2)

# 🔴 RED SECTION: You Gave (Debit / Credit Given)
with col_left:
    st.markdown(
        """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">🔴 YOU GAVE (Debit / Udhari)</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record when you give goods or credit to a customer</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form(key="udhari_form", clear_on_submit=True):
        u_date = st.date_input(
            "Date", datetime.now(), format="DD/MM/YYYY", key="u_date_key"
        )

        existing_outlets = [
            "+ Add New Customer/Outlet"
        ] + st.session_state.outlets_list
        selected_u_outlet = st.selectbox(
            "Customer / Outlet Name", existing_outlets, key="u_outlet_select"
        )

        if selected_u_outlet == "+ Add New Customer/Outlet":
            u_outlet = st.text_input(
                "Enter New Customer/Store Name", key="u_outlet_text"
            )
        else:
            u_outlet = selected_u_outlet

        u_amount = st.number_input(
            "Amount (₹)", min_value=0.0, step=50.0, key="u_amt"
        )
        u_note = st.text_input("Details / Item Notes (Optional)", key="u_note")

        btn_udhari = st.form_submit_button("🔴 Save Entry (You Gave)")

    if btn_udhari:
        if not u_outlet.strip():
            st.error("Please select or enter a valid customer name!")
        elif u_amount <= 0:
            st.error("Please enter a valid amount greater than zero!")
        else:
            final_outlet = save_outlet_name(u_outlet)
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
                f"🔴 Added ₹ {u_amount:,.2f} credit entry for {final_outlet}"
            )
            st.rerun()

# 🟢 GREEN SECTION: You Got (Credit / Payment Received)
with col_right:
    st.markdown(
        """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">🟢 YOU GOT (Credit / Payment)</h3>
            <p style="margin:0; font-size:13px; color:#555;">Record when a customer pays you back</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not st.session_state.outlets_list:
        st.info("No customers saved yet. Please add an entry on the left first.")
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

            p_outlet_df = st.session_state.ledger[
                st.session_state.ledger["Outlet Name"] == p_outlet
            ]
            current_due = (
                p_outlet_df["Balance"].iloc[-1]
                if not p_outlet_df.empty
                else 0.0
            )

            st.info(f"👉 **Current Due for {p_outlet}:** ₹ {current_due:,.2f}")

            p_amount = st.number_input(
                "Received Amount (₹)", min_value=0.0, step=50.0, key="p_amt"
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
                    f"🟢 Received ₹ {p_amount:,.2f} payment from {p_outlet}"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# 3. CUSTOMER LEDGER DASHBOARD & WHATSAPP REMINDER
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Ledger Dashboard & Payment Reminders")

if not st.session_state.outlets_list:
    st.info("No ledger records available to display.")
else:
    selected_view_outlet = st.selectbox(
        "View Customer Khatabook:",
        options=["All Customers"] + st.session_state.outlets_list,
    )

    if selected_view_outlet == "All Customers":
        df_view = st.session_state.ledger.copy()
    else:
        df_view = st.session_state.ledger[
            st.session_state.ledger["Outlet Name"] == selected_view_outlet
        ]

    # Metrics Calculations
    total_given = df_view["Debit (You Gave)"].sum()
    total_got = df_view["Credit (You Got)"].sum()
    total_due = total_given - total_got

    m1, m2, m3 = st.columns(3)
    m1.metric("Total You Gave", f"₹ {total_given:,.2f}")
    m2.metric("Total You Got", f"₹ {total_got:,.2f}")
    m3.metric("🔴 Net Outstanding Due", f"₹ {total_due:,.2f}")

    # Data Table
    st.dataframe(
        df_view[
            [
                "ID",
                "Date",
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
            "Debit (You Gave)": st.column_config.NumberColumn(
                "🔴 You Gave (₹)", format="₹ %.2f"
            ),
            "Credit (You Got)": st.column_config.NumberColumn(
                "🟢 You Got (₹)", format="₹ %.2f"
            ),
            "Balance": st.column_config.NumberColumn(
                "Balance Due (₹)", format="₹ %.2f"
            ),
        },
        hide_index=True,
    )

    # WhatsApp Payment Reminder Feature
    if selected_view_outlet != "All Customers" and total_due > 0:
        st.markdown("### 💬 Send WhatsApp Payment Reminder")
        wa_col1, wa_col2 = st.columns([2, 1])
        with wa_col1:
            phone_num = st.text_input(
                "WhatsApp Number (e.g. 919876543210)", placeholder="91XXXXXXXXXX"
            )
        with wa_col2:
            st.write("")
            st.write("")
            if st.button("📲 Generate Link"):
                if phone_num.strip():
                    msg = f"Hello {selected_view_outlet}, as per our Khatabook record, your total balance due is Rs {total_due:,.2f}. Kindly clear the payment at your earliest convenience. Thank you!"
                    encoded_msg = (
                        pd.Series([msg]).str.replace(" ", "%20").values[0]
                    )
                    url = f"https://api.whatsapp.com/send?phone={phone_num}&text={encoded_msg}"
                    st.markdown(f"[👉 Click Here to Send via WhatsApp]({url})")
                else:
                    st.warning("Please enter a valid phone number!")
