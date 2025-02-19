import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def create_balance_timeline(transactions):
    if transactions.empty:
        return None

    cumsum = transactions['amount'].cumsum()

    fig = px.line(
        x=transactions['date'],
        y=cumsum,
        title='Balance Timeline',
        labels={'x': 'Date', 'y': 'Balance ($)'}
    )

    fig.update_layout(
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    return fig

def create_category_breakdown(transactions):
    if transactions.empty:
        return None

    category_sums = transactions.groupby('category')['amount'].sum()

    fig = px.pie(
        values=category_sums.values,
        names=category_sums.index,
        title='Expenses by Category'
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig

def format_currency(amount):
    return f"${amount:,.2f}"

TRANSACTION_CATEGORIES = [
    "Scout Account Deposit",
    "Dues",
    "Camping",
    "Equipment",
    "Fundraising",
    "Activities",
    "Donations",
    "Other"
]

PATROLS = [
    "Eagle",
    "Wolf",
    "Bear",
    "Tiger",
    "Lion"
]