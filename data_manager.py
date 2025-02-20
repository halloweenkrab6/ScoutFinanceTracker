import pandas as pd
import numpy as np
from datetime import datetime
import os

class ScoutFinanceManager:
    def __init__(self):
        self.transactions_file = "transactions.csv"
        self.scouts_file = "scouts.csv"
        self.troop_balance = 0.0
        self.scouts = pd.DataFrame()  # Initialize empty DataFrame
        self._initialize_data()

    def _initialize_data(self):
        # Initialize scouts first
        if not os.path.exists(self.scouts_file):
            self.scouts = pd.DataFrame({
                'scout_id': [],
                'name': [],
                'patrol': [],
                'email': [],  # Add email field
                'balance': []
            })
            self.scouts.to_csv(self.scouts_file, index=False)
        else:
            self.scouts = pd.read_csv(self.scouts_file)
            # Add email column if it doesn't exist
            if 'email' not in self.scouts.columns:
                self.scouts['email'] = ''
                self.scouts.to_csv(self.scouts_file, index=False)
            self.scouts['balance'] = 0.0  # Reset balances for recalculation

        # Then initialize transactions
        if not os.path.exists(self.transactions_file):
            # Create new transactions file with all columns
            self.transactions = pd.DataFrame({
                'date': [],
                'description': [],
                'category': [],
                'amount': [],
                'scout_id': [],
                'type': [],
                'account_type': [],  # 'troop' or 'scout'
                'affects_troop': []  # Boolean flag for scout transactions that also affect troop
            })
            self.transactions.to_csv(self.transactions_file, index=False)
        else:
            # Load existing transactions
            self.transactions = pd.read_csv(self.transactions_file)
            self.transactions['date'] = pd.to_datetime(self.transactions['date'])

            # Handle legacy data - add account_type if it doesn't exist
            if 'account_type' not in self.transactions.columns:
                self.transactions['account_type'] = 'troop'
                self.transactions.loc[
                    (self.transactions['category'] == 'Scout Account Deposit') & 
                    (self.transactions['scout_id'].notna()),
                    'account_type'
                ] = 'scout'

            # Add affects_troop column if it doesn't exist
            if 'affects_troop' not in self.transactions.columns:
                self.transactions['affects_troop'] = False

            # Save the updated structure
            self.transactions.to_csv(self.transactions_file, index=False)

            # Calculate troop balance
            troop_transactions = self.transactions[
                (self.transactions['account_type'] == 'troop') |
                (self.transactions['affects_troop'] == True)
            ]
            self.troop_balance = troop_transactions['amount'].sum()

            # Recalculate scout balances
            scout_transactions = self.transactions[
                (self.transactions['account_type'] == 'scout') & 
                (self.transactions['scout_id'].notna())
            ]
            for _, trans in scout_transactions.iterrows():
                self._update_scout_balance(
                    int(trans['scout_id']), 
                    trans['amount']
                )

    def add_transaction(self, date, description, category, amount, scout_id, trans_type, affects_troop=False):
        # Determine account type based on category and scout_id
        account_type = 'scout' if category == 'Scout Account Deposit' and scout_id else 'troop'

        new_transaction = pd.DataFrame({
            'date': [pd.to_datetime(date)],
            'description': [description],
            'category': [category],
            'amount': [amount],
            'scout_id': [scout_id],
            'type': [trans_type],
            'account_type': [account_type],
            'affects_troop': [affects_troop]
        })

        self.transactions = pd.concat([self.transactions, new_transaction], ignore_index=True)
        self.transactions.to_csv(self.transactions_file, index=False)

        if account_type == 'scout' and scout_id:
            self._update_scout_balance(scout_id, amount if trans_type == 'credit' else -amount)
            if affects_troop:
                self.troop_balance += (amount if trans_type == 'credit' else -amount)
        elif account_type == 'troop':
            self.troop_balance += (amount if trans_type == 'credit' else -amount)

    def _update_scout_balance(self, scout_id, amount):
        if scout_id in self.scouts['scout_id'].values:
            self.scouts.loc[self.scouts['scout_id'] == scout_id, 'balance'] += amount
            self.scouts.to_csv(self.scouts_file, index=False)

    def add_scout(self, name, patrol, email):  # Add email parameter
        scout_id = len(self.scouts) + 1
        new_scout = pd.DataFrame({
            'scout_id': [scout_id],
            'name': [name],
            'patrol': [patrol],
            'email': [email],  # Add email field
            'balance': [0.0]
        })
        self.scouts = pd.concat([self.scouts, new_scout], ignore_index=True)
        self.scouts.to_csv(self.scouts_file, index=False)
        return scout_id

    def edit_scout(self, scout_id, name=None, patrol=None, email=None):
        """Edit a scout's information."""
        if scout_id in self.scouts['scout_id'].values:
            if name is not None:
                self.scouts.loc[self.scouts['scout_id'] == scout_id, 'name'] = name
            if patrol is not None:
                self.scouts.loc[self.scouts['scout_id'] == scout_id, 'patrol'] = patrol
            if email is not None:
                self.scouts.loc[self.scouts['scout_id'] == scout_id, 'email'] = email
            self.scouts.to_csv(self.scouts_file, index=False)
            return True
        return False

    def get_scout(self, scout_id):
        """Get a scout's information."""
        if scout_id in self.scouts['scout_id'].values:
            return self.scouts[self.scouts['scout_id'] == scout_id].iloc[0].to_dict()
        return None

    def get_troop_balance(self):
        return self.troop_balance

    def get_scout_balance(self, scout_id):
        if scout_id in self.scouts['scout_id'].values:
            return self.scouts.loc[self.scouts['scout_id'] == scout_id, 'balance'].iloc[0]
        return 0.0

    def get_transactions(self, start_date=None, end_date=None, scout_id=None, category=None):
        transactions = self.transactions.copy()

        if start_date:
            transactions = transactions[transactions['date'] >= pd.to_datetime(start_date)]
        if end_date:
            transactions = transactions[transactions['date'] <= pd.to_datetime(end_date)]
        if scout_id:
            transactions = transactions[
                (transactions['scout_id'] == scout_id) |
                (transactions['account_type'] == 'troop')
            ]
        if category:
            transactions = transactions[transactions['category'] == category]

        return transactions.sort_values('date', ascending=False)

    def export_transactions(self):
        return self.transactions.to_csv(index=False)