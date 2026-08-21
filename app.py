import streamlit as st
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Coca-Cola Credit Tracker", layout="wide")

st.title("🥤 Coca-Cola Distribution - Credit & Ledger App")
st.subheader("500+ Outlets, Category & Manager Wise Accounting")

# 1. Session State Initialization
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "ID", "Date", "Outlet Name", "Category", "Manager", "Udhari (Debit)", "Payment (Credit)", "Balance"
    ])

# 2. Sidebar Entry Form
st.sidebar.header("➕ नई एंट्री दर्ज करें (New Entry)")
entry_date = st.sidebar.date_input("Entry Date (तारीख)", datetime.now())
outlet_name = st.sidebar.text_input("Outlet Name (दुकान का नाम)")
category = st.sidebar.selectbox("Category", ["Kirana Store", "Supermarket", "Hotel/Restaurant", "Pan Shop / Kiosk"])
manager = st.sidebar.selectbox("Assigned Manager", ["PIYUSH YADAV", "RUKSHAT ALAM", "SUMIT MGR", "PRAKASH MGR"])
trans_type = st.sidebar.radio("Transaction Type", ["Udhari (Debit)", "Payment Received (Credit)"])
amount = st.sidebar.number_input("Amount (₹)", min_value=0.0, step=100.0)

if st.sidebar.button("Save Entry (रजिस्टर करें)"):
    if outlet_name.strip() == "":
        st.sidebar.error("कृपया आउटलेट का नाम दर्ज करें!")
    else:
        debit = amount if trans_type == "Udhari (Debit)" else 0
        credit = amount if trans_type == "Payment Received (Credit)" else 0
        
        # Balance calculation for specific outlet
        outlet_df = st.session_state.ledger[st.session_state.ledger["Outlet Name"] == outlet_name]
        prev_balance = outlet_df["Balance"].iloc[-1] if not outlet_df.empty else 0
        current_balance = prev_balance + debit - credit

        new_entry = {
            "ID": len(st.session_state.ledger) + 1,
            "Date": entry_date.strftime("%d-%b-%Y"),
            "Outlet Name": outlet_name,
            "Category": category,
            "Manager": manager,
            "Udhari (Debit)": debit,
            "Payment (Credit)": credit,
            "Balance": current_balance
        }
        
        st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_entry])], ignore_index=True)
        st.sidebar.success("Entry Saved Successfully!")

# 3. Dynamic Filters
st.markdown("---")
st.subheader("🔍 लेजर और उधारी फ़िल्टर (Filters)")

col1, col2, col3 = st.columns(3)
with col1:
    filter_outlet = st.selectbox("Outlet Wise", ["All Outlets"] + list(st.session_state.ledger['Outlet Name'].unique()))
with col2:
    filter_cat = st.selectbox("Category Wise", ["All Categories"] + list(st.session_state.ledger['Category'].unique()))
with col3:
    filter_mgr = st.selectbox("Manager Wise", ["All Managers"] + list(st.session_state.ledger['Manager'].unique()))

# Filter Logic
df_display = st.session_state.ledger.copy()

if filter_outlet != "All Outlets":
    df_display = df_display[df_display['Outlet Name'] == filter_outlet]
if filter_cat != "All Categories":
    df_display = df_display[df_display['Category'] == filter_cat]
if filter_mgr != "All Managers":
    df_display = df_display[df_display['Manager'] == filter_mgr]

# 4. Total Dues Summary Cards
st.markdown("---")
st.subheader("📊 कुल बकाया और हिसाब समरी (Total Dues Summary)")

total_debit = df_display["Udhari (Debit)"].sum() if not df_display.empty else 0
total_credit = df_display["Payment (Credit)"].sum() if not df_display.empty else 0
total_dues = total_debit - total_credit

m1, m2, m3 = st.columns(3)
m1.metric("कुल उधारी (Total Debit)", f"₹ {total_debit:,.2f}")
m2.metric("कुल जमा (Total Paid)", f"₹ {total_credit:,.2f}")
m3.metric("🔴 कुल बकाया राशि (Total Net Dues)", f"₹ {total_dues:,.2f}")

# 5. Ledger Table with Delete Option
st.markdown("---")
st.subheader("📋 उधारी और पेमेंट रिकॉर्ड (Ledger Records)")

if df_display.empty:
    st.info("कोई रिकॉर्ड नहीं मिला।")
else:
    for index, row in df_display.iterrows():
        c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1, 2, 2, 2, 2, 2, 2, 2, 1])
        c1.write(f"#{row['ID']}")
        c2.write(row['Date'])
        c3.write(row['Outlet Name'])
        c4.write(row['Category'])
        c5.write(row['Manager'])
        c6.write(f"₹ {row['Udhari (Debit)']}")
        c7.write(f"₹ {row['Payment (Credit)']}")
        c8.write(f"**₹ {row['Balance']}**")
        
        # Entry Delete Option
        if c9.button("❌", key=f"del_{row['ID']}"):
            st.session_state.ledger = st.session_state.ledger[st.session_state.ledger['ID'] != row['ID']]
            st.rerun()

# 6. PDF Generation Function
def create_pdf(dataframe, total_dues_amount):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("<b>Coca-Cola Distribution - Credit Statement</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    dues_text = Paragraph(f"<b>Total Outstanding Dues: ₹ {total_dues_amount:,.2f}</b>", styles['Heading2'])
    elements.append(dues_text)
    elements.append(Spacer(1, 12))

    # Table Header & Data
    data = [["ID", "Date", "Outlet Name", "Category", "Manager", "Debit", "Credit", "Balance"]]
    for _, row in dataframe.iterrows():
        data.append([
            str(row["ID"]),
            str(row["Date"]),
            str(row["Outlet Name"]),
            str(row["Category"]),
            str(row["Manager"]),
            f"Rs.{row['Udhari (Debit)']}",
            f"Rs.{row['Payment (Credit)']}",
            f"Rs.{row['Balance']}"
        ])

    pdf_table = Table(data)
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    elements.append(pdf_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 7. PDF Export & WhatsApp Section
st.markdown("---")
st.subheader("📄 PDF स्टेटमेंट और WhatsApp शेयरिंग")

col_pdf1, col_pdf2 = st.columns(2)

with col_pdf1:
    if not df_display.empty:
        pdf_data = create_pdf(df_display, total_dues)
        st.download_button(
            label="📥 Download PDF Statement",
            data=pdf_data,
            file_name=f"CocaCola_Statement_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    else:
        st.write("PDF जनरेट करने के लिए डेटा होना ज़रूरी है।")

with col_pdf2:
    whatsapp_num = st.text_input("WhatsApp नंबर (Country Code के साथ, जैसे 919876543210)")
    if st.button("WhatsApp पर Dues मैसेज भेजें"):
        if whatsapp_num:
            msg = f"नमस्ते, आपका कुल बकाया हिसाब (Total Dues) ₹ {total_dues:,.2f} है।"
            st.success(f"WhatsApp लिंक: https://wa.me/{whatsapp_num}?text={msg}")
        else:
            st.warning("कृपया व्हाट्सएप नंबर दर्ज करें!")
