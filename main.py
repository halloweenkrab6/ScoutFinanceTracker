import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data_manager import ScoutFinanceManager
from utils import (
    create_balance_timeline,
    create_category_breakdown,
    format_currency,
    TRANSACTION_CATEGORIES,
    PATROLS
)
from styles import apply_custom_styles

# Initialize session state
if 'finance_manager' not in st.session_state:
    st.session_state.finance_manager = ScoutFinanceManager()

# Apply custom styles
apply_custom_styles()

st.title("🏕️ Boy Scout Troop Finance Tracker")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["Dashboard", "Transactions", "Scouts", "Reports"])

if page == "Dashboard":
    # Display total balance
    total_balance = st.session_state.finance_manager.get_total_balance()
    st.header("Troop Balance")
    st.metric("Current Balance", format_currency(total_balance))
    
    # Show balance timeline
    st.subheader("Balance Timeline")
    transactions = st.session_state.finance_manager.get_transactions()
    timeline = create_balance_timeline(transactions)
    if timeline:
        st.plotly_chart(timeline, use_container_width=True)
    
    # Show category breakdown
    st.subheader("Expense Categories")
    breakdown = create_category_breakdown(transactions)
    if breakdown:
        st.plotly_chart(breakdown, use_container_width=True)

elif page == "Transactions":
    st.header("Transaction Management")
    
    # Transaction entry form
    with st.form("transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.today())
            description = st.text_input("Description")
            category = st.selectbox("Category", TRANSACTION_CATEGORIES)
        with col2:
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
            scout_data = st.session_state.finance_manager.scouts
            scout_options = [None] + list(scout_data['scout_id'])
            scout_id = st.selectbox("Scout (optional)", 
                                    options=scout_options,
                                    format_func=lambda x: "Troop" if x is None else f"{scout_data.loc[scout_data['scout_id'] == x, 'name'].iloc[0]} (ID: {x})")
            trans_type = st.radio("Type", ["credit", "debit"])
        
        submit = st.form_submit_button("Add Transaction")
        if submit:
            st.session_state.finance_manager.add_transaction(
                date, description, category, 
                amount if trans_type == 'credit' else -amount,
                scout_id, trans_type
            )
            st.success("Transaction added successfully!")
    
    # Transaction history
    st.subheader("Transaction History")
    transactions = st.session_state.finance_manager.get_transactions()
    if not transactions.empty:
        st.dataframe(transactions.style.format({
            'amount': format_currency,
            'date': lambda x: x.strftime('%Y-%m-%d')
        }))
        
        # Export option
        if st.button("Export to CSV"):
            csv = st.session_state.finance_manager.export_transactions()
            st.download_button(
                "Download CSV",
                csv,
                "scout_transactions.csv",
                "text/csv"
            )

elif page == "Scouts":
    st.header("Scout Management")
    
    # Add new scout
    with st.form("scout_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Scout Name")
        with col2:
            patrol = st.selectbox("Patrol", PATROLS)
        
        submit = st.form_submit_button("Add Scout")
        if submit and name:
            scout_id = st.session_state.finance_manager.add_scout(name, patrol)
            st.success(f"Scout added successfully! Scout ID: {scout_id}")
    
    # Display scout balances
    st.subheader("Scout Balances")
    scouts = st.session_state.finance_manager.scouts
    if not scouts.empty:
        st.dataframe(scouts.style.format({
            'balance': format_currency
        }))

elif page == "Reports":
    st.header("Financial Reports")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                  datetime.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.today())
    
    # Filter options
    scout_data = st.session_state.finance_manager.scouts
    scout_filter = st.selectbox(
        "Filter by Scout",
        options=[None] + list(scout_data['scout_id']),
        format_func=lambda x: "All Scouts" if x is None else f"{scout_data.loc[scout_data['scout_id'] == x, 'name'].iloc[0]} (ID: {x})"
    )
    
    category_filter = st.selectbox(
        "Filter by Category",
        options=[None] + TRANSACTION_CATEGORIES,
        format_func=lambda x: "All Categories" if x is None else x
    )
    
    # Display filtered transactions
    filtered_transactions = st.session_state.finance_manager.get_transactions(
        start_date, end_date, scout_filter, category_filter
    )
    
    if not filtered_transactions.empty:
        st.dataframe(filtered_transactions.style.format({
            'amount': format_currency,
            'date': lambda x: x.strftime('%Y-%m-%d')
        }))
        
        # Summary statistics
        total = filtered_transactions['amount'].sum()
        credits = filtered_transactions[filtered_transactions['amount'] > 0]['amount'].sum()
        debits = filtered_transactions[filtered_transactions['amount'] < 0]['amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", format_currency(total))
        col2.metric("Total Credits", format_currency(credits))
        col3.metric("Total Debits", format_currency(debits))
    else:
        st.info("No transactions found for the selected filters.")

# Footer
st.markdown("---")
st.markdown("Boy Scout Troop Finance Tracker - Made with ❤️ by Scout Leaders")