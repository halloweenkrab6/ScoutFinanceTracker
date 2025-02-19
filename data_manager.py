import pandas as pd
import numpy as np
from datetime import datetime
import os

class ScoutFinanceManager:
    def __init__(self):
        self.transactions_file = "transactions.csv"
        self.scouts_file = "scouts.csv"
        self._initialize_data()

    def _initialize_data(self):
        if not os.path.exists(self.transactions_file):
            self.transactions = pd.DataFrame({
                'date': [],
                'description': [],
                'category': [],
                'amount': [],
                'scout_id': [],
                'type': []
            })
            self.transactions.to_csv(self.transactions_file, index=False)
        else:
            self.transactions = pd.read_csv(self.transactions_file)
            self.transactions['date'] = pd.to_datetime(self.transactions['date'])

        if not os.path.exists(self.scouts_file):
            self.scouts = pd.DataFrame({
                'scout_id': [],
                'name': [],
                'patrol': [],
                'balance': []
            })
            self.scouts.to_csv(self.scouts_file, index=False)
        else:
            self.scouts = pd.read_csv(self.scouts_file)

    def add_transaction(self, date, description, category, amount, scout_id, trans_type):
        new_transaction = pd.DataFrame({
            'date': [pd.to_datetime(date)],
            'description': [description],
            'category': [category],
            'amount': [amount],
            'scout_id': [scout_id],
            'type': [trans_type]
        })
        self.transactions = pd.concat([self.transactions, new_transaction], ignore_index=True)
        self.transactions.to_csv(self.transactions_file, index=False)
        
        if scout_id:
            self._update_scout_balance(scout_id, amount if trans_type == 'credit' else -amount)

    def _update_scout_balance(self, scout_id, amount):
        if scout_id in self.scouts['scout_id'].values:
            self.scouts.loc[self.scouts['scout_id'] == scout_id, 'balance'] += amount
            self.scouts.to_csv(self.scouts_file, index=False)

    def add_scout(self, name, patrol):
        scout_id = len(self.scouts) + 1
        new_scout = pd.DataFrame({
            'scout_id': [scout_id],
            'name': [name],
            'patrol': [patrol],
            'balance': [0.0]
        })
        self.scouts = pd.concat([self.scouts, new_scout], ignore_index=True)
        self.scouts.to_csv(self.scouts_file, index=False)
        return scout_id

    def get_total_balance(self):
        return self.transactions['amount'].sum()

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
            transactions = transactions[transactions['scout_id'] == scout_id]
        if category:
            transactions = transactions[transactions['category'] == category]
            
        return transactions.sort_values('date', ascending=False)

    def export_transactions(self):
        return self.transactions.to_csv(index=False)
