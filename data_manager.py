import os

import pandas as pd

# Direct money movement between one scout and the troop account.
TRANSACTION_TYPES = ["Deposit", "Refund"]
# Everything that shows up in a ledger: transactions plus events.
LEDGER_TYPES = TRANSACTION_TYPES + ["Event"]

PATROLS = ["Eagle", "Wolf", "Bear", "Tiger", "Lion", "Unassigned"]

SCOUT_COLS = ["scout_id", "name", "age", "patrol", "email", "balance"]
PARENT_COLS = ["scout_id", "name", "phone", "email"]
TXN_COLS = ["transaction_id", "date", "description", "transaction_type", "scout_id", "amount"]
EVENT_COLS = ["event_id", "date", "name", "notes", "attendee_ids"]
EXPENSE_COLS = ["expense_id", "event_id", "name", "unit_price", "troop_paid", "charge_all"]
CHARGE_COLS = ["event_id", "expense_id", "scout_id", "amount_override"]
LEDGER_COLS = ["transaction_id", "date", "description", "transaction_type",
               "amount", "bank_delta", "scout_delta", "scout_ids"]


class ScoutFinanceManager:
    """Owns all troop data and derives balances from it.

    Scout balance = deposits - refunds - event charges.
    Bank balance  = deposits - refunds - what the troop paid out for events.
    """

    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.bank_balance = 0.0
        self._load()

    # ── Loading ─────────────────────────────────────────────────────────────

    def _load(self):
        s = self._read("scouts.csv", SCOUT_COLS + ["parent_names"])
        s["scout_id"] = s["scout_id"].astype(int)
        s["age"] = pd.to_numeric(s["age"], errors="coerce").fillna(0).astype(int)
        s["balance"] = 0.0
        self.scouts = s[SCOUT_COLS].copy()

        p = self._read("parents.csv", PARENT_COLS)
        p["scout_id"] = p["scout_id"].astype(int)
        self.parents = p
        self._migrate_parent_names(s)

        t = self._read("transactions.csv", TXN_COLS)
        t["scout_id"] = t["scout_id"].astype(int)
        t["amount"] = t["amount"].astype(float)
        self.transactions = t

        self.events = self._read("events.csv", EVENT_COLS)

        x = self._read("event_expenses.csv", EXPENSE_COLS)
        x["unit_price"] = pd.to_numeric(x["unit_price"], errors="coerce").fillna(0.0)
        x["troop_paid"] = pd.to_numeric(x["troop_paid"], errors="coerce").fillna(0.0)
        x["charge_all"] = x["charge_all"].astype(str).str.lower() == "true"
        self.expenses = x

        c = self._read("event_charges.csv", CHARGE_COLS)
        c["scout_id"] = c["scout_id"].astype(int)
        c["amount_override"] = pd.to_numeric(c["amount_override"], errors="coerce")
        self.charges = c

        self._recalculate_balances()

    def _migrate_parent_names(self, legacy_scouts):
        """Move the old free-text parent_names column into parents.csv."""
        path = os.path.join(self.data_dir, "scouts.csv")
        if "parent_names" not in pd.read_csv(path, nrows=0).columns:
            return
        rows = [{"scout_id": sid, "name": n.strip(), "phone": "", "email": ""}
                for sid, names in zip(legacy_scouts["scout_id"], legacy_scouts["parent_names"])
                if sid not in set(self.parents["scout_id"])
                for n in str(names).split(",") if n.strip()]
        if rows:
            self.parents = pd.concat([self.parents, pd.DataFrame(rows, columns=PARENT_COLS)],
                                     ignore_index=True)
            self._save_parents()
        self._save_scouts()

    def _read(self, name, cols):
        path = os.path.join(self.data_dir, name)
        if not os.path.exists(path):
            df = pd.DataFrame(columns=cols)
            df.to_csv(path, index=False)
            return df
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return df.reindex(columns=cols, fill_value="")

    def _recalculate_balances(self):
        signed = self._signed_amounts()
        charges = self._charge_amounts()

        per_scout = signed.groupby(self.transactions["scout_id"]).sum()
        per_scout = per_scout.sub(charges.groupby("scout_id")["amount"].sum(), fill_value=0.0)
        self.scouts["balance"] = self.scouts["scout_id"].map(per_scout).fillna(0.0).astype(float)
        self.bank_balance = float(signed.sum() - self.expenses["troop_paid"].sum())

    def _signed_amounts(self):
        sign = self.transactions["transaction_type"].map({"Deposit": 1.0, "Refund": -1.0}).fillna(0.0)
        return self.transactions["amount"] * sign

    def _charge_amounts(self):
        """Every charge with its effective amount (custom amount, else the expense price)."""
        m = self.charges.merge(self.expenses[["expense_id", "unit_price"]],
                               on="expense_id", how="inner")
        m["amount"] = m["amount_override"].fillna(m["unit_price"]).astype(float)
        return m

    # ── Scouts ──────────────────────────────────────────────────────────────

    def add_scout(self, name, age, patrol, email, parents=()):
        scout_id = int(self.scouts["scout_id"].max()) + 1 if not self.scouts.empty else 1
        self.scouts = pd.concat([self.scouts, pd.DataFrame([{
            "scout_id": scout_id, "name": name, "age": int(age),
            "patrol": patrol, "email": email, "balance": 0.0,
        }])], ignore_index=True)
        self._save_scouts()
        if parents:
            self.set_parents(scout_id, parents)
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

    def get_parents(self, scout_id):
        return self.parents[self.parents["scout_id"] == scout_id].reset_index(drop=True)

    def set_parents(self, scout_id, parents):
        """Replace a scout's parents with a list of dicts: name, phone, email."""
        rows = pd.DataFrame([{"scout_id": int(scout_id), "name": p["name"],
                              "phone": p.get("phone", ""), "email": p.get("email", "")}
                             for p in parents], columns=PARENT_COLS)
        self.parents = pd.concat([self.parents[self.parents["scout_id"] != scout_id], rows],
                                 ignore_index=True)
        self._save_parents()

    def get_parent_names(self):
        """{scout_id: "Name, Name"} for every scout with parents on file."""
        return self.parents.groupby("scout_id")["name"].agg(", ".join).to_dict()

    # ── Transactions ────────────────────────────────────────────────────────

    def add_transaction(self, date, transaction_type, scout_id, amount, description=""):
        if transaction_type not in TRANSACTION_TYPES:
            raise ValueError(f"Unknown transaction type: {transaction_type}")
        txn_id = self._next_id(self.transactions["transaction_id"], "TXN")
        self.transactions = pd.concat([self.transactions, pd.DataFrame([{
            "transaction_id": txn_id,
            "date": pd.to_datetime(date).strftime("%Y-%m-%d"),
            "description": description,
            "transaction_type": transaction_type,
            "scout_id": int(scout_id),
            "amount": abs(float(amount)),
        }])], ignore_index=True)
        self._save_transactions()
        self._recalculate_balances()
        return txn_id

    def delete_transaction(self, txn_id):
        self.transactions = self.transactions[self.transactions["transaction_id"] != txn_id]
        self._save_transactions()
        self._recalculate_balances()

    # ── Events ──────────────────────────────────────────────────────────────

    def create_event(self, name, date, notes="", attendee_ids=()):
        event_id = self._next_id(self.events["event_id"], "EVT")
        self.events = pd.concat([self.events, pd.DataFrame([{
            "event_id": event_id,
            "date": pd.to_datetime(date).strftime("%Y-%m-%d"),
            "name": name,
            "notes": notes,
            "attendee_ids": self._join_ids(attendee_ids),
        }])], ignore_index=True)
        self._save_events()
        return event_id

    def get_event(self, event_id):
        row = self.events[self.events["event_id"] == event_id]
        if row.empty:
            return None
        ev = row.iloc[0].to_dict()
        ev["attendee_ids"] = self._parse_ids(ev["attendee_ids"])
        return ev

    def get_event_expenses(self, event_id):
        return (self.expenses[self.expenses["event_id"] == event_id]
                .sort_values("expense_id").reset_index(drop=True))

    def get_event_charges(self, event_id):
        ch = self._charge_amounts()
        return ch[ch["event_id"] == event_id].reset_index(drop=True)

    def save_event(self, event_id, name, date, notes, attendee_ids, expenses, charged, overrides):
        """Replace an event's details, expenses and charges in one go.

        expenses  -- list of dicts: expense_id (None for a new line), name,
                     unit_price, troop_paid, charge_all
        charged   -- set of (scout_id, expense_id) pairs ticked in the grid; the
                     grid only covers attendees and expenses that were already saved
        overrides -- {(scout_id, expense_id): amount} custom amounts

        Newly added attendees and newly added expenses are charged automatically
        wherever the expense has charge_all set. Returns the override pairs that
        were dropped because that scout isn't charged for that expense.
        """
        old = self.get_event(event_id)
        old_attendees = set(old["attendee_ids"])
        attendees = list(dict.fromkeys(int(s) for s in attendee_ids))

        mask = self.events["event_id"] == event_id
        self.events.loc[mask, "name"] = name
        self.events.loc[mask, "date"] = pd.to_datetime(date).strftime("%Y-%m-%d")
        self.events.loc[mask, "notes"] = notes
        self.events.loc[mask, "attendee_ids"] = self._join_ids(attendees)

        existing_ids = set(self.get_event_expenses(event_id)["expense_id"])
        rows, new_ids = [], set()
        for e in expenses:
            xid = e.get("expense_id")
            if xid not in existing_ids:
                xid = self._next_id(pd.concat([self.expenses["expense_id"],
                                               pd.Series([r["expense_id"] for r in rows])]), "EXP")
                new_ids.add(xid)
            rows.append({
                "expense_id": xid, "event_id": event_id, "name": e["name"],
                "unit_price": float(e["unit_price"]), "troop_paid": float(e["troop_paid"]),
                "charge_all": bool(e["charge_all"]),
            })
        self.expenses = pd.concat([
            self.expenses[self.expenses["event_id"] != event_id],
            pd.DataFrame(rows, columns=EXPENSE_COLS),
        ], ignore_index=True)

        final_ids = {r["expense_id"] for r in rows}
        charge_all = {r["expense_id"] for r in rows if r["charge_all"]}
        pairs = {(int(s), x) for s, x in charged if s in attendees and x in final_ids}
        for s in attendees:
            for x in charge_all:
                if s not in old_attendees or x in new_ids:
                    pairs.add((s, x))

        dropped = [p for p in overrides if p not in pairs]
        new_charges = pd.DataFrame([{
            "event_id": event_id, "expense_id": x, "scout_id": s,
            "amount_override": overrides.get((s, x)),
        } for s, x in sorted(pairs)], columns=CHARGE_COLS)
        self.charges = pd.concat([self.charges[self.charges["event_id"] != event_id], new_charges],
                                 ignore_index=True)
        self.charges["amount_override"] = pd.to_numeric(self.charges["amount_override"], errors="coerce")

        self._save_events()
        self._recalculate_balances()
        return dropped

    def delete_event(self, event_id):
        self.events = self.events[self.events["event_id"] != event_id]
        self.expenses = self.expenses[self.expenses["event_id"] != event_id]
        self.charges = self.charges[self.charges["event_id"] != event_id]
        self._save_events()
        self._recalculate_balances()

    def get_event_summaries(self):
        charged = self._charge_amounts().groupby("event_id")["amount"].sum()
        paid = self.expenses.groupby("event_id")["troop_paid"].sum()
        df = self.events.copy()
        df["attendees"] = df["attendee_ids"].map(lambda s: len(self._parse_ids(s)))
        df["charged"] = df["event_id"].map(charged).fillna(0.0)
        df["troop_paid"] = df["event_id"].map(paid).fillna(0.0)
        df["net"] = df["charged"] - df["troop_paid"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.sort_values("date", ascending=False).reset_index(drop=True)

    # ── Ledger & queries ────────────────────────────────────────────────────

    def get_ledger(self, scout_ids=None):
        """Transactions and events as one table, newest first.

        With scout_ids, only those scouts' transactions and event charges are
        included, and events carry no bank impact (the troop's payout isn't
        attributable to individual scouts).
        """
        sel = set(scout_ids) if scout_ids is not None else None
        rows = []

        signed = self._signed_amounts()
        for (_, t), amt in zip(self.transactions.iterrows(), signed):
            if sel is not None and t["scout_id"] not in sel:
                continue
            rows.append({
                "transaction_id": t["transaction_id"], "date": t["date"],
                "description": t["description"], "transaction_type": t["transaction_type"],
                "amount": amt, "bank_delta": amt, "scout_delta": amt,
                "scout_ids": str(t["scout_id"]),
            })

        charges = self._charge_amounts()
        paid = self.expenses.groupby("event_id")["troop_paid"].sum()
        for _, ev in self.events.iterrows():
            ch = charges[charges["event_id"] == ev["event_id"]]
            attendees = self._parse_ids(ev["attendee_ids"])
            if sel is not None:
                ch = ch[ch["scout_id"].isin(sel)]
                attendees = [s for s in attendees if s in sel]
                if ch.empty and not attendees:
                    continue
            total = float(ch["amount"].sum())
            rows.append({
                "transaction_id": ev["event_id"], "date": ev["date"],
                "description": ev["name"], "transaction_type": "Event",
                "amount": -total,
                "bank_delta": 0.0 if sel is not None else -float(paid.get(ev["event_id"], 0.0)),
                "scout_delta": -total,
                "scout_ids": self._join_ids(attendees),
            })

        df = pd.DataFrame(rows, columns=LEDGER_COLS)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.sort_values("date", ascending=False).reset_index(drop=True)

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
        ledger = self.get_ledger([scout_id])
        if ledger.empty:
            return ""
        cols = ["transaction_id", "date", "description", "transaction_type", "scout_delta"]
        return ledger[cols].rename(columns={"scout_delta": "amount"}).to_csv(index=False)

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _next_id(existing, prefix):
        nums = []
        for v in existing.dropna():
            try:
                nums.append(int(str(v).split("-")[1]))
            except (IndexError, ValueError):
                pass
        return f"{prefix}-{str(max(nums, default=0) + 1).zfill(3)}"

    @staticmethod
    def _parse_ids(scout_ids_str):
        s = str(scout_ids_str).strip()
        if not s or s == "nan":
            return []
        try:
            return [int(float(x.strip())) for x in s.split(",")
                    if x.strip() and x.strip() != "nan"]
        except ValueError:
            return []

    @staticmethod
    def _join_ids(ids):
        return ",".join(str(int(i)) for i in ids)

    def _save_scouts(self):
        self.scouts.to_csv(os.path.join(self.data_dir, "scouts.csv"), index=False)

    def _save_parents(self):
        self.parents.to_csv(os.path.join(self.data_dir, "parents.csv"), index=False)

    def _save_transactions(self):
        self.transactions.to_csv(os.path.join(self.data_dir, "transactions.csv"), index=False)

    def _save_events(self):
        self.events.to_csv(os.path.join(self.data_dir, "events.csv"), index=False)
        self.expenses.to_csv(os.path.join(self.data_dir, "event_expenses.csv"), index=False)
        self.charges.to_csv(os.path.join(self.data_dir, "event_charges.csv"), index=False)
