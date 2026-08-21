import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Coca-Cola Credit Tracker", layout="wide")

st.title("🥤 Coca-Cola Distribution - Credit & Ledger App")
st.subheader("500+ Outlets & Manager Wise Accounting")

# Sample Data Framework
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "ID", "Date", "Outlet Name", "Category", "Manager", "Udhari (Debit)", "Payment (Credit)", "Balance"
    ])

# Sidebar - Entry Form
st.sidebar.header("➕ नई एंट्री दर्ज करें (New Entry)")
entry_date = st.sidebar.date_input("Entry Date (तारीख)", datetime.now())
outlet_name = st.sidebar.text_input("Outlet Name (दुकान का नाम)")
category = st.sidebar.selectbox("Category", ["Kirana Store", "Supermarket", "Hotel/Restaurant", "Pan Shop"])
manager = st.sidebar.selectbox("Assigned Manager", ["Ramesh Kumar", "Suresh Verma", "Amit Singh"])
trans_type = st.sidebar.radio("Transaction Type", ["Udhari (Debit)", "Payment Received (Credit)"])
amount = st.sidebar.number_input("Amount (₹)", min_value=0.0, step=100.0)

if st.sidebar.button("Save Entry (रजिस्टर करें)"):
    debit = amount if trans_type == "Udhari (Debit)" else 0
    credit = amount if trans_type == "Payment Received (Credit)" else 0
    
    new_entry = {
        "ID": len(st.session_state.ledger) + 1,
        "Date": entry_date.strftime("%d-%b-%Y"),
        "Outlet Name": outlet_name,
        "Category": category,
        "Manager": manager,
        "Udhari (Debit)": debit,
        "Payment (Credit)": credit,
        "Balance": debit - credit
    }
    st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_entry])], ignore_index=True)
    st.sidebar.success("Entry Saved Successfully!")

# Main Dashboard Filter
col1, col2 = st.columns(2)
with col1:
    filter_cat = st.selectbox("Filter by Category", ["All"] + list(st.session_state.ledger['Category'].unique()))
with col2:
    filter_mgr = st.selectbox("Filter by Manager", ["All"] + list(st.session_state.ledger['Manager'].unique()))

# Filter Logic
df_display = st.session_state.ledger.copy()
if filter_cat != "All":
    df_display = df_display[df_display['Category'] == filter_cat]
if filter_mgr != "All":
    df_display = df_display[df_display['Manager'] == filter_mgr]

st.dataframe(df_display, use_container_width=True)

# WhatsApp Export Mock
st.markdown("---")
st.subheader("📲 Export & Share Ledger")
whatsapp_num = st.text_input("Enter WhatsApp Number with Country Code (e.g., 919876543210)")
if st.button("Share Statement on WhatsApp"):
    st.success(f"PDF Statement Link Generated for WhatsApp: https://wa.me/{whatsapp_num}")