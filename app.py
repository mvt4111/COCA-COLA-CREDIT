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

st.title("📕 डिजिटल खाताबुक (Khatabook App)")
st.caption("ग्राहकों और आउटलेट्स का उधारी व पेमेंट हिसाब-किताब")

# ------------------------------------------------------------------------------
# 1. STATE MANAGEMENT (Auto Outlet/Customer Saving)
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


# Sidebar Data Backup
with st.sidebar.expander("💾 बैकअप और डेटा रीस्टोर"):
    uploaded_file = st.file_uploader("CSV फ़ाइल अपलोड करें", type=["csv"])
    if uploaded_file is not None:
        try:
            st.session_state.ledger = pd.read_csv(uploaded_file)
            st.session_state.outlets_list = sorted(
                list(st.session_state.ledger["Outlet Name"].dropna().unique())
            )
            st.success("डेटा सफलतापूर्वक लोड हो गया!")
        except Exception as e:
            st.error(f"Error: {e}")

    if not st.session_state.ledger.empty:
        csv_buffer = st.session_state.ledger.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 डाउनलोड खाताबुक डेटा (CSV)",
            data=csv_buffer,
            file_name=f"khatabook_backup_{datetime.now().strftime('%d-%m-%Y')}.csv",
            mime="text/csv",
        )

# ------------------------------------------------------------------------------
# 2. KHATABOOK STYLE ENTRY SECTION (Red / Green Cards)
# ------------------------------------------------------------------------------
st.markdown("---")

col_left, col_right = st.columns(2)

# 🔴 RED SECTION: Aapne Diya (Udhari / Debit)
with col_left:
    st.markdown(
        """
        <div class="red-card">
            <h3 style="color: #C9302C; margin:0;">🔴 आपने दिया (You Gave / उधारी)</h3>
            <p style="margin:0; font-size:13px; color:#555;">जब ग्राहक को सामान या उधारी दें</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form(key="udhari_form", clear_on_submit=True):
        u_date = st.date_input(
            "तारीख (Date)", datetime.now(), format="DD/MM/YYYY", key="u_date_key"
        )

        existing_outlets = [
            "+ नया ग्राहक/आउटलेट जोड़ें"
        ] + st.session_state.outlets_list
        selected_u_outlet = st.selectbox(
            "ग्राहक / आउटलेट का नाम", existing_outlets, key="u_outlet_select"
        )

        if selected_u_outlet == "+ नया ग्राहक/आउटलेट जोड़ें":
            u_outlet = st.text_input(
                "नए ग्राहक/दुकान का नाम लिखें", key="u_outlet_text"
            )
        else:
            u_outlet = selected_u_outlet

        u_amount = st.number_input(
            "राशि (Amount ₹)", min_value=0.0, step=50.0, key="u_amt"
        )
        u_note = st.text_input(
            "विवरण / सामान की जानकारी (Optional)", key="u_note"
        )

        btn_udhari = st.form_submit_button("🔴 उधारी सेव करें")

    if btn_udhari:
        if not u_outlet.strip():
            st.error("कृपया ग्राहक या आउटलेट का नाम दर्ज करें!")
        elif u_amount <= 0:
            st.error("कृपया मान्य राशि दर्ज करें!")
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
                "Type": "🔴 Udhari (You Gave)",
                "Debit (You Gave)": float(u_amount),
                "Credit (You Got)": 0.0,
                "Balance": float(new_balance),
                "Note": u_note if u_note else "उधारी बिल",
            }

            st.session_state.ledger = pd.concat(
                [st.session_state.ledger, pd.DataFrame([entry])],
                ignore_index=True,
            )
            st.success(f"🔴 ₹ {u_amount:,.2f} उधारी दर्ज की गई ({final_outlet})")
            st.rerun()

# 🟢 GREEN SECTION: Aapko Mila (Payment Jama / Credit)
with col_right:
    st.markdown(
        """
        <div class="green-card">
            <h3 style="color: #4CAE4C; margin:0;">🟢 आपको मिला (You Got / जमा)</h3>
            <p style="margin:0; font-size:13px; color:#555;">जब ग्राहक से भुगतान या किश्त प्राप्त हो</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not st.session_state.outlets_list:
        st.info("अभी कोई ग्राहक सेव नहीं है। पहले उधारी एंट्री दर्ज करें।")
    else:
        with st.form(key="payment_form", clear_on_submit=True):
            p_date = st.date_input(
                "तारीख (Date)",
                datetime.now(),
                format="DD/MM/YYYY",
                key="p_date_key",
            )
            p_outlet = st.selectbox(
                "ग्राहक / आउटलेट चुनें",
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

            st.info(f"👉 **{p_outlet} का कुल बकाया:** ₹ {current_due:,.2f}")

            p_amount = st.number_input(
                "प्राप्त राशि (Amount ₹)", min_value=0.0, step=50.0, key="p_amt"
            )
            p_mode = st.selectbox(
                "भुगतान का तरीका (Payment Mode)",
                ["Cash", "UPI / PhonePe / GPay", "Bank Transfer", "Cheque"],
                key="p_mode",
            )

            btn_payment = st.form_submit_button("🟢 पेमेंट जमा करें")

        if btn_payment:
            if p_amount <= 0:
                st.error("कृपया मान्य राशि दर्ज करें!")
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
                    "Type": "🟢 Jama (You Got)",
                    "Debit (You Gave)": 0.0,
                    "Credit (You Got)": float(p_amount),
                    "Balance": float(new_balance),
                    "Note": f"पेमेंट ({p_mode})",
                }

                st.session_state.ledger = pd.concat(
                    [st.session_state.ledger, pd.DataFrame([entry])],
                    ignore_index=True,
                )
                st.success(
                    f"🟢 ₹ {p_amount:,.2f} जमा दर्ज किया गया ({p_outlet})"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# 3. CUSTOMER LEDGER DASHBOARD & WHATSAPP REMINDER
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 ग्राहक का लेज़र हिसाब एवं रिमाइंड")

if not st.session_state.outlets_list:
    st.info("अभी कोई लेज़र रिकॉर्ड उपलब्ध नहीं है।")
else:
    selected_view_outlet = st.selectbox(
        "ग्राहक का खाताबुक देखें:",
        options=["सभी ग्राहक (All Outlets)"] + st.session_state.outlets_list,
    )

    if selected_view_outlet == "सभी ग्राहक (All Outlets)":
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
    m1.metric("कुल दिया (Total Gave)", f"₹ {total_given:,.2f}")
    m2.metric("कुल मिला (Total Got)", f"₹ {total_got:,.2f}")
    m3.metric("🔴 कुल बकाया (Net Dues)", f"₹ {total_due:,.2f}")

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
            "Date": st.column_config.TextColumn("तारीख (DD-MM-YYYY)"),
            "Debit (You Gave)": st.column_config.NumberColumn(
                "🔴 आपने दिया (₹)", format="₹ %.2f"
            ),
            "Credit (You Got)": st.column_config.NumberColumn(
                "🟢 आपको मिला (₹)", format="₹ %.2f"
            ),
            "Balance": st.column_config.NumberColumn(
                "बकाया (Balance ₹)", format="₹ %.2f"
            ),
        },
        hide_index=True,
    )

    # WhatsApp Payment Reminder Feature
    if selected_view_outlet != "सभी ग्राहक (All Outlets)" and total_due > 0:
        st.markdown("### 💬 WhatsApp तकादा (Payment Reminder)")
        wa_col1, wa_col2 = st.columns([2, 1])
        with wa_col1:
            phone_num = st.text_input(
                "व्हाट्सएप नंबर (जैसे: 919876543210)", placeholder="91XXXXXXXXXX"
            )
        with wa_col2:
            st.write("")
            st.write("")
            if st.button("📲 रिमाइंडर भेजें"):
                if phone_num.strip():
                    msg = f"नमस्ते {selected_view_outlet}, खाताबुक के अनुसार आपका कुल बकाया ₹ {total_due:,.2f} है। कृपया जल्द से जल्द भुगतान करें। धन्यवाद!"
                    encoded_msg = (
                        pd.Series([msg]).str.replace(" ", "%20").values[0]
                    )
                    url = f"https://api.whatsapp.com/send?phone={phone_num}&text={encoded_msg}"
                    st.markdown(f"[👉 WhatsApp पर भेजें]({url})")
                else:
                    st.warning("कृपया व्हाट्सएप नंबर दर्ज करें!")
