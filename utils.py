import plotly.graph_objects as go
import pandas as pd

TRANSACTION_TYPES = [
    "EventIncome", "CampoutExpense", "EventExpense", "Fee", "Deposit", "Transfer"
]

PATROLS = ["Eagle", "Wolf", "Bear", "Tiger", "Lion", "Unassigned"]

# (bg, text, display label)
TYPE_META = {
    "EventIncome":    ("#d1fae5", "#065f46", "Event Income"),
    "CampoutExpense": ("#fed7aa", "#9a3412", "Campout Expense"),
    "EventExpense":   ("#fee2e2", "#991b1b", "Event Expense"),
    "Fee":            ("#fef3c7", "#92400e", "Fee"),
    "Deposit":        ("#dbeafe", "#1e40af", "Deposit"),
    "Transfer":       ("#ede9fe", "#5b21b6", "Transfer"),
}

# Multipliers for auto-populating bank_delta / scout_delta in Register
TYPE_DEFAULTS = {
    "EventIncome":    {"bank":  1, "scout":  0, "needs_scouts": False},
    "CampoutExpense": {"bank": -1, "scout":  0, "needs_scouts": False},
    "EventExpense":   {"bank": -1, "scout":  0, "needs_scouts": False},
    "Fee":            {"bank":  0, "scout": -1, "needs_scouts": True},
    "Deposit":        {"bank":  1, "scout":  1, "needs_scouts": True},
    "Transfer":       {"bank":  0, "scout":  0, "needs_scouts": False},
}


def format_currency(amount):
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return "$0.00"
    sign = "-" if amt < 0 else ""
    return f"{sign}${abs(amt):,.2f}"


def badge_html(txn_type):
    bg, fg, label = TYPE_META.get(str(txn_type), ("#f3f4f6", "#374151", str(txn_type)))
    return (
        f'<span style="background:{bg};color:{fg};padding:3px 10px;'
        f'border-radius:999px;font-size:11px;font-weight:600;'
        f'white-space:nowrap;display:inline-block;letter-spacing:.01em">{label}</span>'
    )


def txn_table_html(df, scout_lookup=None, show_scouts=True):
    if df is None or (hasattr(df, "empty") and df.empty):
        return (
            '<div style="text-align:center;padding:48px 0;color:#9ca3af;font-size:14px">'
            'No transactions found.</div>'
        )

    scouts_th = "<th>Scouts</th>" if show_scouts else ""
    rows_html = ""

    for _, row in df.iterrows():
        txn_type = str(row.get("transaction_type", ""))
        amount = float(row.get("amount", 0) or 0)
        bank_d = float(row.get("bank_delta", 0) or 0)
        scout_d = float(row.get("scout_delta", 0) or 0)

        amt_color = "#16a34a" if amount >= 0 else "#dc2626"

        try:
            date_str = pd.to_datetime(row.get("date")).strftime("%b %d, %Y")
        except Exception:
            date_str = str(row.get("date", ""))

        txn_id = str(row.get("transaction_id", ""))
        desc = str(row.get("description", "") or "").strip()

        # Deltas
        delta_parts = []
        if bank_d != 0:
            c = "#16a34a" if bank_d >= 0 else "#dc2626"
            delta_parts.append(f'<span style="color:{c}">B:{format_currency(bank_d)}</span>')
        if scout_d != 0:
            c = "#16a34a" if scout_d >= 0 else "#dc2626"
            delta_parts.append(f'<span style="color:{c}">S:{format_currency(scout_d)}</span>')
        delta_html = "&nbsp; ".join(delta_parts) if delta_parts else "—"

        # Scouts column
        scouts_td_content = ""
        if show_scouts and scout_lookup:
            if txn_type == "Transfer":
                fi = _safe_int(row.get("from_scout_id"))
                ti = _safe_int(row.get("to_scout_id"))
                parts = []
                if fi and fi in scout_lookup:
                    parts.append(f"↓ {scout_lookup[fi]}")
                if ti and ti in scout_lookup:
                    parts.append(f"↑ {scout_lookup[ti]}")
                scouts_td_content = " / ".join(parts) or "—"
            else:
                ids = _parse_ids(str(row.get("scout_ids", "")))
                names = [scout_lookup[i] for i in ids if i in scout_lookup]
                scouts_td_content = ", ".join(names) if names else "—"

        scouts_td = (
            f'<td style="font-size:12px;color:#6b7280;padding:11px 14px">'
            f'{scouts_td_content}</td>'
        ) if show_scouts else ""

        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6">
          <td style="font-family:monospace;font-size:11px;color:#9ca3af;padding:11px 14px;white-space:nowrap">{txn_id}</td>
          <td style="white-space:nowrap;color:#6b7280;font-size:13px;padding:11px 14px">{date_str}</td>
          <td style="font-weight:500;color:#111827;padding:11px 14px">{desc or '<em style="color:#9ca3af">—</em>'}</td>
          <td style="padding:11px 14px">{badge_html(txn_type)}</td>
          <td style="font-weight:700;color:{amt_color};text-align:right;white-space:nowrap;padding:11px 14px">{format_currency(amount)}</td>
          <td style="font-size:11px;padding:11px 14px;white-space:nowrap">{delta_html}</td>
          {scouts_td}
        </tr>"""

    return f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #e5e7eb">
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:white">
      <thead>
        <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
          <th style="{_th()}">ID</th>
          <th style="{_th()}">Date</th>
          <th style="{_th()}">Description</th>
          <th style="{_th()}">Type</th>
          <th style="{_th()} text-align:right">Amount</th>
          <th style="{_th()}">Deltas</th>
          {scouts_th if show_scouts else ""}
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>"""


def _th():
    return ("text-align:left;padding:10px 14px;font-size:11px;"
            "text-transform:uppercase;letter-spacing:.05em;color:#6b7280;font-weight:600;")


def create_balance_chart(transactions):
    if transactions is None or (hasattr(transactions, "empty") and transactions.empty):
        return None
    df = transactions.sort_values("date").copy()
    if "bank_delta" not in df.columns:
        return None
    df["running"] = df["bank_delta"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["running"],
        mode="lines+markers",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=5, color="#2563eb"),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.07)",
        hovertemplate="%{x|%b %d, %Y}<br><b>$%{y:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=0),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, height=210,
        xaxis=dict(showgrid=True, gridcolor="#f3f4f6", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6", tickprefix="$",
                   zeroline=True, zerolinecolor="#e5e7eb"),
        hovermode="x unified",
    )
    return fig


def create_type_breakdown(transactions):
    if transactions is None or (hasattr(transactions, "empty") and transactions.empty):
        return None
    df = transactions.copy()
    df["abs"] = df["amount"].abs()
    summary = df.groupby("transaction_type")["abs"].sum().reset_index()
    colors = [TYPE_META.get(t, ("#94a3b8", "#fff", t))[0] for t in summary["transaction_type"]]
    fig = go.Figure(go.Pie(
        labels=summary["transaction_type"],
        values=summary["abs"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="percent",
        hovertemplate="%{label}<br><b>$%{value:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=0),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=True, height=210,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)),
    )
    return fig


def _safe_int(val):
    try:
        s = str(val).strip()
        if s and s not in ("", "nan", "None"):
            return int(float(s))
    except Exception:
        pass
    return None


def _parse_ids(scout_ids_str):
    s = str(scout_ids_str).strip()
    if not s or s == "nan":
        return []
    try:
        return [int(float(x.strip())) for x in s.split(",")
                if x.strip() and x.strip() != "nan"]
    except Exception:
        return []
