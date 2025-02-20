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

if 'editing_scout' not in st.session_state:
    st.session_state.editing_scout = None

# Apply custom styles
apply_custom_styles()

st.title("🏕️ Boy Scout Troop Finance Tracker")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["Dashboard", "Transactions", "Scouts", "Reports"])

if page == "Dashboard":
    # Display troop balance
    troop_balance = st.session_state.finance_manager.get_troop_balance()
    st.header("Troop Account")
    st.metric("Troop Balance", format_currency(troop_balance))

    # Show balance timeline
    st.subheader("Balance Timeline")
    transactions = st.session_state.finance_manager.get_transactions()
    timeline = create_balance_timeline(transactions[transactions['account_type'] == 'troop'])
    if timeline:
        st.plotly_chart(timeline, use_container_width=True)

    # Show category breakdown
    st.subheader("Expense Categories")
    troop_transactions = transactions[transactions['account_type'] == 'troop']
    breakdown = create_category_breakdown(troop_transactions)
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
            # Rename Amount to Bank Amount and add Scout Account Amount
            if category == "Scout Account Deposit":
                bank_amount = st.number_input("Bank Amount", min_value=0.0, step=0.01,
                    help="Amount deposited to the bank")
                scout_amount = st.number_input("Scout Account Amount", min_value=0.0, step=0.01,
                    help="Amount credited to scout's account (may differ from bank amount)")
            else:
                amount = st.number_input("Amount", min_value=0.0, step=0.01)

            scout_data = st.session_state.finance_manager.scouts
            scout_options = [None] + list(scout_data['scout_id'])
            scout_id = st.selectbox("Scout (optional)", 
                                    options=scout_options,
                                    format_func=lambda x: "Troop" if x is None else f"{scout_data.loc[scout_data['scout_id'] == x, 'name'].iloc[0]} (ID: {x})")
            trans_type = st.radio("Type", ["credit", "debit"])

        # Show option to affect troop account for scout transactions
        affects_troop = False
        if category == "Scout Account Deposit" and scout_id:
            affects_troop = st.checkbox("Also affect Troop account", 
                help="When checked, this Scout Account transaction will also impact the Troop's balance")

        # Show warning for Scout Account Deposits
        if category == "Scout Account Deposit" and not scout_id:
            st.warning("Please select a Scout for Scout Account Deposits")

        submit = st.form_submit_button("Add Transaction")
        if submit:
            if category == "Scout Account Deposit" and not scout_id:
                st.error("A Scout must be selected for Scout Account Deposits")
            else:
                # Use appropriate amount values based on transaction type
                if category == "Scout Account Deposit":
                    amount_val = bank_amount if trans_type == 'credit' else -bank_amount
                    scout_amount_val = scout_amount if trans_type == 'credit' else -scout_amount
                else:
                    amount_val = amount if trans_type == 'credit' else -amount
                    scout_amount_val = amount_val  # For non-scout deposits, amounts are the same

                st.session_state.finance_manager.add_transaction(
                    date, description, category, 
                    amount_val, scout_amount_val,
                    scout_id, trans_type, affects_troop
                )
                st.success("Transaction added successfully!")

    # Transaction history
    st.subheader("Transaction History")
    transactions = st.session_state.finance_manager.get_transactions()
    if not transactions.empty:
        # Add account type and affects troop columns to display
        transactions['Account'] = transactions.apply(
            lambda x: (
                f"{scout_data.loc[scout_data['scout_id'] == x['scout_id'], 'name'].iloc[0]}'s Account" +
                (" (affects Troop)" if x['affects_troop'] else "")
            ) if x['account_type'] == 'scout' and not pd.isna(x['scout_id']) 
            else "Troop Account", 
            axis=1
        )

        # Show both amounts for Scout Account Deposits
        if 'scout_amount' in transactions.columns: #Check if column exists to avoid error
          display_df = transactions[['date', 'description', 'category', 'amount', 'scout_amount', 'Account']]
          st.dataframe(display_df.style.format({
              'amount': format_currency,
              'scout_amount': format_currency,
              'date': lambda x: x.strftime('%Y-%m-%d')
          }).set_properties(**{
              'amount': [{'color': 'blue'}],
              'scout_amount': [{'color': 'green'}]
          }))
        else:
          display_df = transactions[['date', 'description', 'category', 'amount', 'Account']]
          st.dataframe(display_df.style.format({
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
            email = st.text_input("Email")  # Add email input
        with col2:
            patrol = st.selectbox("Patrol", PATROLS)

        submit = st.form_submit_button("Add Scout")
        if submit and name:
            if '@' not in email:  # Basic email validation
                st.error("Please enter a valid email address")
            else:
                scout_id = st.session_state.finance_manager.add_scout(name, patrol, email)
                st.success(f"Scout added successfully! Scout ID: {scout_id}")

    # Display scout balances with edit buttons
    st.subheader("Scout Account Balances")
    scouts = st.session_state.finance_manager.scouts
    if not scouts.empty:
        # Create columns for the table and edit buttons
        col1, col2 = st.columns([3, 1])

        with col1:
            # Display scouts table
            display_scouts = scouts[['scout_id', 'name', 'email', 'patrol', 'balance']]
            st.dataframe(display_scouts.style.format({
                'balance': format_currency
            }))

        with col2:
            # Add edit button for each scout
            scout_to_edit = st.selectbox(
                "Select Scout to Edit",
                options=list(scouts['scout_id']),
                format_func=lambda x: scouts.loc[scouts['scout_id'] == x, 'name'].iloc[0]
            )

            if st.button("Edit Selected Scout"):
                st.session_state.editing_scout = scout_to_edit

        # Edit form
        if st.session_state.editing_scout is not None:
            st.subheader(f"Edit Scout Information")
            scout_info = st.session_state.finance_manager.get_scout(st.session_state.editing_scout)

            with st.form("edit_scout_form"):
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    edit_name = st.text_input("Name", value=scout_info['name'])
                    edit_email = st.text_input("Email", value=scout_info['email'])
                with edit_col2:
                    edit_patrol = st.selectbox("Patrol", PATROLS, index=PATROLS.index(scout_info['patrol']))

                if st.form_submit_button("Save Changes"):
                    if '@' not in edit_email:
                        st.error("Please enter a valid email address")
                    else:
                        if st.session_state.finance_manager.edit_scout(
                            st.session_state.editing_scout,
                            name=edit_name,
                            patrol=edit_patrol,
                            email=edit_email
                        ):
                            st.success("Scout information updated successfully!")
                            st.session_state.editing_scout = None
                            st.experimental_rerun()

            if st.button("Cancel Editing"):
                st.session_state.editing_scout = None
                st.experimental_rerun()

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
        # Add account type column
        filtered_transactions['Account'] = filtered_transactions.apply(
            lambda x: f"{scout_data.loc[scout_data['scout_id'] == x['scout_id'], 'name'].iloc[0]}'s Account" 
            if x['account_type'] == 'scout' and not pd.isna(x['scout_id']) 
            else "Troop Account", axis=1
        )

        display_df = filtered_transactions[['date', 'description', 'category', 'amount', 'Account']]
        st.dataframe(display_df.style.format({
            'amount': format_currency,
            'date': lambda x: x.strftime('%Y-%m-%d')
        }))

        # Summary statistics
        troop_transactions = filtered_transactions[filtered_transactions['account_type'] == 'troop']
        scout_transactions = filtered_transactions[filtered_transactions['account_type'] == 'scout']

        st.subheader("Summary")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Troop Account**")
            troop_total = troop_transactions['amount'].sum()
            troop_credits = troop_transactions[troop_transactions['amount'] > 0]['amount'].sum()
            troop_debits = troop_transactions[troop_transactions['amount'] < 0]['amount'].sum()

            st.metric("Total", format_currency(troop_total))
            st.metric("Credits", format_currency(troop_credits))
            st.metric("Debits", format_currency(troop_debits))

        with col2:
            st.markdown("**Scout Accounts**")
            scout_total = scout_transactions['amount'].sum()
            scout_credits = scout_transactions[scout_transactions['amount'] > 0]['amount'].sum()
            scout_debits = scout_transactions[scout_transactions['amount'] < 0]['amount'].sum()

            st.metric("Total", format_currency(scout_total))
            st.metric("Credits", format_currency(scout_credits))
            st.metric("Debits", format_currency(scout_debits))
    else:
        st.info("No transactions found for the selected filters.")

# Footer
st.markdown("---")
st.markdown("Boy Scout Troop Finance Tracker - Made with ❤️ by Scout Leaders")