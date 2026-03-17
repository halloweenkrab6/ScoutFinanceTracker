import pandas as pd
import os

TRANSACTION_TYPES = [
    "EventIncome", "CampoutExpense", "EventExpense", "Fee", "Deposit", "Transfer", "Other"
]

PATROLS = ["Eagle", "Wolf", "Bear", "Tiger", "Lion", "Unassigned"]


class ScoutFinanceManager:
    def __init__(self):
        self.transactions_file = "transactions.csv"
        self.scouts_file = "scouts.csv"
        self.bank_balance = 0.0
        self._load()

    # ── Loading & Migration ──────────────────────────────────────────────────

    def _load(self):
        self._load_scouts()
        self._load_transactions()
        self._recalculate_balances()

    def _load_scouts(self):
        if not os.path.exists(self.scouts_file):
            self.scouts = pd.DataFrame(columns=[
                "scout_id", "name", "age", "parent_names", "patrol", "email", "balance"
            ])
            self._save_scouts()
            return

        self.scouts = pd.read_csv(self.scouts_file)
        changed = False
        for col, default in [("age", 0), ("parent_names", ""), ("email", ""), ("balance", 0.0)]:
            if col not in self.scouts.columns:
                self.scouts[col] = default
                changed = True
        if changed:
            self._save_scouts()

    def _load_transactions(self):
        if not os.path.exists(self.transactions_file):
            self.transactions = pd.DataFrame(columns=[
                "transaction_id", "date", "description", "transaction_type",
                "amount", "bank_delta", "scout_delta", "scout_ids",
                "from_scout_id", "to_scout_id",
            ])
            self._save_transactions()
            return

        self.transactions = pd.read_csv(self.transactions_file)
        self.transactions["date"] = pd.to_datetime(self.transactions["date"], errors="coerce")
        self._migrate_transactions()

    def _migrate_transactions(self):
        changed = False

        if "transaction_id" not in self.transactions.columns:
            self.transactions.insert(
                0, "transaction_id",
                [f"TXN-{str(i + 1).zfill(3)}" for i in range(len(self.transactions))]
            )
            changed = True

        if "transaction_type" not in self.transactions.columns:
            cat_map = {
                "Scout Account Deposit": "Deposit",
                "Dues": "Fee",
                "Camping": "CampoutExpense",
                "Equipment": "EventExpense",
                "Fundraising": "EventIncome",
                "Activities": "EventExpense",
                "Donations": "EventIncome",
                "Other": "EventIncome",
            }
            src = (self.transactions["category"]
                   if "category" in self.transactions.columns
                   else pd.Series("Other", index=self.transactions.index))
            self.transactions["transaction_type"] = src.map(cat_map).fillna("EventExpense")
            changed = True

        if "bank_delta" not in self.transactions.columns:
            def _bd(row):
                at = row.get("account_type", "troop")
                af = str(row.get("affects_troop", "False")).lower() in ("true", "1")
                amt = float(row.get("amount", 0) or 0)
                if at == "troop":
                    return amt
                return amt if af else 0.0
            self.transactions["bank_delta"] = self.transactions.apply(_bd, axis=1)
            changed = True

        if "scout_delta" not in self.transactions.columns:
            def _sd(row):
                if row.get("account_type", "troop") == "scout":
                    return float(row.get("amount", 0) or 0)
                return 0.0
            self.transactions["scout_delta"] = self.transactions.apply(_sd, axis=1)
            changed = True

        if "scout_ids" not in self.transactions.columns:
            def _sids(row):
                sid = row.get("scout_id", "")
                if pd.notna(sid) and str(sid).strip() not in ("", "nan"):
                    return str(int(float(sid)))
                return ""
            self.transactions["scout_ids"] = self.transactions.apply(_sids, axis=1)
            changed = True

        for col in ("from_scout_id", "to_scout_id"):
            if col not in self.transactions.columns:
                self.transactions[col] = ""
                changed = True

        if changed:
            self._save_transactions()

    def _recalculate_balances(self):
        self.scouts["balance"] = 0.0
        self.bank_balance = 0.0
        if self.transactions.empty:
            return

        for _, txn in self.transactions.iterrows():
            self.bank_balance += float(txn.get("bank_delta", 0) or 0)
            t_type = str(txn.get("transaction_type", "")).strip()

            if t_type == "Transfer":
                from_id = self._safe_int(txn.get("from_scout_id"))
                to_id = self._safe_int(txn.get("to_scout_id"))
                amt = float(txn.get("amount", 0) or 0)
                if from_id is not None:
                    self._adj(from_id, -amt)
                if to_id is not None:
                    self._adj(to_id, amt)
            else:
                delta = float(txn.get("scout_delta", 0) or 0)
                if delta != 0:
                    for sid in self._parse_ids(txn.get("scout_ids", "")):
                        self._adj(sid, delta)

    # ── CRUD ────────────────────────────────────────────────────────────────

    def add_scout(self, name, age, parent_names, patrol, email):
        scout_id = int(self.scouts["scout_id"].max()) + 1 if not self.scouts.empty else 1
        self.scouts = pd.concat([self.scouts, pd.DataFrame([{
            "scout_id": scout_id, "name": name, "age": int(age),
            "parent_names": parent_names, "patrol": patrol,
            "email": email, "balance": 0.0,
        }])], ignore_index=True)
        self._save_scouts()
        return scout_id

    def edit_scout(self, scout_id, **kwargs):
        mask = self.scouts["scout_id"] == scout_id
        if not mask.any():
            return False
        for k, v in kwargs.items():
            if k in self.scouts.columns:
                self.scouts.loc[mask, k] = v
        self._save_scouts()
        return True

    def get_scout(self, scout_id):
        row = self.scouts[self.scouts["scout_id"] == scout_id]
        return row.iloc[0].to_dict() if not row.empty else None

    def add_transaction(self, date, description, transaction_type, amount,
                        bank_delta, scout_delta, scout_ids,
                        from_scout_id=None, to_scout_id=None):
        txn_id = self._next_id()
        self.transactions = pd.concat([self.transactions, pd.DataFrame([{
            "transaction_id": txn_id,
            "date": pd.to_datetime(date),
            "description": description,
            "transaction_type": transaction_type,
            "amount": float(amount),
            "bank_delta": float(bank_delta),
            "scout_delta": float(scout_delta),
            "scout_ids": ",".join(str(s) for s in scout_ids),
            "from_scout_id": from_scout_id or "",
            "to_scout_id": to_scout_id or "",
        }])], ignore_index=True)
        self._save_transactions()

        self.bank_balance += float(bank_delta)
        if transaction_type == "Transfer":
            if from_scout_id:
                self._adj(int(from_scout_id), -float(amount))
            if to_scout_id:
                self._adj(int(to_scout_id), float(amount))
        else:
            for sid in scout_ids:
                self._adj(int(sid), float(scout_delta))
        self._save_scouts()
        return txn_id

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_all_transactions(self):
        if self.transactions.empty:
            return pd.DataFrame()
        return self.transactions.sort_values("date", ascending=False).reset_index(drop=True)

    def get_scout_transactions(self, scout_id):
        if self.transactions.empty:
            return pd.DataFrame()
        sid_str = str(scout_id)

        def _match(row):
            if str(row.get("transaction_type", "")) == "Transfer":
                return (str(row.get("from_scout_id", "")) == sid_str or
                        str(row.get("to_scout_id", "")) == sid_str)
            return scout_id in self._parse_ids(row.get("scout_ids", ""))

        mask = self.transactions.apply(_match, axis=1)
        return self.transactions[mask].sort_values("date", ascending=False).reset_index(drop=True)

    def get_bank_balance(self):
        return self.bank_balance

    def get_troop_account_balance(self):
        return self.bank_balance - float(self.scouts["balance"].sum())

    def get_gross_assets(self):
        return (self.bank_balance
                + self.get_troop_account_balance()
                + self.get_negative_scout_sum())

    def get_positive_scout_sum(self):
        return float(self.scouts[self.scouts["balance"] > 0]["balance"].sum())

    def get_negative_scout_sum(self):
        return float(self.scouts[self.scouts["balance"] < 0]["balance"].sum())

    def export_scout_ledger(self, scout_id):
        txns = self.get_scout_transactions(scout_id)
        if txns.empty:
            return ""
        cols = [c for c in ["transaction_id", "date", "description",
                             "transaction_type", "amount", "scout_delta"]
                if c in txns.columns]
        return txns[cols].to_csv(index=False)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _next_id(self):
        if self.transactions.empty:
            return "TXN-001"
        nums = []
        for tid in self.transactions["transaction_id"].dropna():
            try:
                nums.append(int(str(tid).split("-")[1]))
            except Exception:
                pass
        return f"TXN-{str(max(nums) + 1 if nums else 1).zfill(3)}"

    def _adj(self, scout_id, amount):
        mask = self.scouts["scout_id"] == int(scout_id)
        if mask.any():
            self.scouts.loc[mask, "balance"] = self.scouts.loc[mask, "balance"] + amount

    @staticmethod
    def _parse_ids(scout_ids_str):
        s = str(scout_ids_str).strip()
        if not s or s == "nan":
            return []
        try:
            return [int(float(x.strip())) for x in s.split(",")
                    if x.strip() and x.strip() != "nan"]
        except Exception:
            return []

    @staticmethod
    def _safe_int(val):
        try:
            s = str(val).strip()
            if s and s not in ("", "nan", "None"):
                return int(float(s))
        except Exception:
            pass
        return None

    def _save_scouts(self):
        self.scouts.to_csv(self.scouts_file, index=False)

    def _save_transactions(self):
        self.transactions.to_csv(self.transactions_file, index=False)
