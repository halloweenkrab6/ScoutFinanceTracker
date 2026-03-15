import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from data_manager import ScoutFinanceManager, TRANSACTION_TYPES, PATROLS
from utils import (
    format_currency, badge_html, txn_table_html,
    create_balance_chart, create_type_breakdown,
    TYPE_DEFAULTS, TYPE_META,
)
from styles import apply_styles

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scout Finance Tracker",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "fm": None,
    "page": "dashboard",
    "selected_scout": None,
    "reg_key": 0,
    "flash": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.fm is None:
    st.session_state.fm = ScoutFinanceManager()

fm: ScoutFinanceManager = st.session_state.fm


# ── Navigation helpers ────────────────────────────────────────────────────────
def goto(page, scout_id=None):
    st.session_state.page = page
    st.session_state.selected_scout = scout_id
    st.rerun()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
_TOP_PAGE = {
    "dashboard": "dashboard",
    "scouts": "scouts",
    "scout_detail": "scouts",
    "register": "register",
    "reports": "reports",
}

NAV_ITEMS = [
    ("dashboard", "📊  Dashboard"),
    ("scouts",    "👥  Scouts"),
    ("register",  "✚  Register"),
    ("reports",   "📈  Reports"),
]
NAV_LABELS = [lbl for _, lbl in NAV_ITEMS]
NAV_MAP    = {lbl: pid for pid, lbl in NAV_ITEMS}

current_top  = _TOP_PAGE.get(st.session_state.page, "dashboard")
current_lbl  = next(lbl for pid, lbl in NAV_ITEMS if pid == current_top)
current_idx  = NAV_LABELS.index(current_lbl)

with st.sidebar:
    st.markdown("""
    <div style="padding:24px 20px 18px;border-bottom:1px solid rgba(255,255,255,0.07)">
      <div style="font-size:26px;margin-bottom:5px">⚜️</div>
      <div style="font-size:15px;font-weight:700;color:white;letter-spacing:-0.02em">Scout Finance</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-top:2px;letter-spacing:.02em">TROOP TRACKER</div>
    </div>
    <div style="height:10px"></div>
    """, unsafe_allow_html=True)

    selected_lbl = st.radio("nav", NAV_LABELS, index=current_idx,
                            label_visibility="collapsed")
    selected_pid = NAV_MAP[selected_lbl]

    # Navigate if top-level changed
    if selected_pid != current_top:
        goto(selected_pid)

    # Quick-stats footer
    bank = fm.get_bank_balance()
    scout_cnt = len(fm.scouts)
    st.markdown(f"""
    <div style="margin-top:auto;padding:16px 12px 22px;border-top:1px solid rgba(255,255,255,0.07)">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;
                  color:rgba(255,255,255,0.3);margin-bottom:10px;font-weight:600">Quick View</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:7px">
        <span style="font-size:12px;color:rgba(255,255,255,0.45)">Bank</span>
        <span style="font-size:13px;font-weight:700;color:{'#4ade80' if bank>=0 else '#f87171'}">{format_currency(bank)}</span>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span style="font-size:12px;color:rgba(255,255,255,0.45)">Scouts</span>
        <span style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.65)">{scout_cnt} members</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Shared helpers ────────────────────────────────────────────────────────────
def scout_lookup():
    if fm.scouts.empty:
        return {}
    return dict(zip(fm.scouts["scout_id"].astype(int), fm.scouts["name"]))


def stat_card(icon, label, value, color=""):
    return f"""
    <div class="stat-card">
      <div class="stat-icon">{icon}</div>
      <div class="stat-label">{label}</div>
      <div class="stat-value {color}">{value}</div>
    </div>"""


def section_header(title):
    st.markdown(f'<div class="section-hdr">{title}</div>', unsafe_allow_html=True)


def sort_df(df, key_prefix):
    available = [c for c in ["date", "amount", "transaction_type"] if c in df.columns]
    c1, c2 = st.columns([2, 1])
    with c1:
        col = st.selectbox("Sort by", available, key=f"{key_prefix}_col",
                           format_func=str.capitalize)
    with c2:
        if col == "date":
            opts = ["Newest first", "Oldest first"]
        else:
            opts = ["High → Low", "Low → High"]
        direction = st.selectbox("Order", opts, key=f"{key_prefix}_dir")
    asc = direction in ("Oldest first", "Low → High")
    return df.sort_values(col, ascending=asc)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown('<h1 class="page-title">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Troop financial overview</p>', unsafe_allow_html=True)

    bank  = fm.get_bank_balance()
    troop = fm.get_troop_account_balance()
    gross = fm.get_gross_assets()
    pos   = fm.get_positive_scout_sum()
    neg   = fm.get_negative_scout_sum()

    cols = st.columns(5)
    cards = [
        ("💰", "Gross Assets",          format_currency(gross), ""),
        ("🏦", "Bank Balance",          format_currency(bank),  "green" if bank >= 0 else "red"),
        ("⚜️", "Troop Account",         format_currency(troop), "green" if troop >= 0 else "red"),
        ("👤", "Scout Balances (+)",    format_currency(pos),   "green"),
        ("⚠️", "Scout Balances (−)",    format_currency(neg),   "red"),
    ]
    for col, (icon, label, val, color) in zip(cols, cards):
        with col:
            st.markdown(stat_card(icon, label, val, color), unsafe_allow_html=True)

    # Charts
    txns = fm.get_all_transactions()
    if not txns.empty:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        ch1, ch2 = st.columns([3, 2])
        with ch1:
            st.markdown('<div class="card"><div class="card-title">Bank Balance Timeline</div>',
                        unsafe_allow_html=True)
            fig = create_balance_chart(txns)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with ch2:
            st.markdown('<div class="card"><div class="card-title">By Transaction Type</div>',
                        unsafe_allow_html=True)
            fig2 = create_type_breakdown(txns)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    # Full ledger
    section_header("Full Ledger")
    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No transactions yet</div>
          <div class="empty-sub">Head to Register to record your first transaction</div>
        </div>""", unsafe_allow_html=True)
    else:
        sl = scout_lookup()
        sorted_txns = sort_df(txns, "dash")
        st.markdown(txn_table_html(sorted_txns, scout_lookup=sl), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: SCOUT LIST
# ═════════════════════════════════════════════════════════════════════════════
def page_scouts():
    st.markdown('<h1 class="page-title">Scouts</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Manage members and view account balances</p>',
                unsafe_allow_html=True)

    # Add scout
    with st.expander("➕  Add New Scout"):
        with st.form("add_scout", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Full Name *")
                age  = st.number_input("Age", 0, 25, 12)
            with c2:
                patrol      = st.selectbox("Patrol", PATROLS)
                email       = st.text_input("Email")
            with c3:
                parent_names = st.text_input("Parent / Guardian")
            if st.form_submit_button("Add Scout", use_container_width=True):
                if not name.strip():
                    st.error("Name is required.")
                else:
                    sid = fm.add_scout(name.strip(), int(age), parent_names.strip(),
                                       patrol, email.strip())
                    st.success(f"Scout added — ID: {sid}")
                    st.rerun()

    if fm.scouts.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">👥</div>
          <div class="empty-title">No scouts yet</div>
          <div class="empty-sub">Use the form above to add your first scout</div>
        </div>""", unsafe_allow_html=True)
        return

    # Search
    search = st.text_input("", placeholder="🔍  Search by name or patrol…",
                           label_visibility="collapsed")
    scouts = fm.scouts.copy()
    if search:
        mask = (scouts["name"].str.contains(search, case=False, na=False) |
                scouts["patrol"].str.contains(search, case=False, na=False))
        scouts = scouts[mask]

    st.markdown(
        f"<div style='font-size:12px;color:#6b7280;margin-bottom:10px'>"
        f"{len(scouts)} scout{'s' if len(scouts) != 1 else ''}</div>",
        unsafe_allow_html=True)

    # Table
    rows_html = ""
    for _, s in scouts.iterrows():
        sid = int(s["scout_id"])
        bal = float(s["balance"])
        bal_color = "#16a34a" if bal >= 0 else "#dc2626"
        age_disp  = int(s["age"]) if pd.notna(s.get("age")) and s.get("age") else "—"
        parents   = str(s.get("parent_names", "") or "").strip() or "—"
        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6;cursor:pointer"
            onmouseover="this.style.background='#f0f9ff'"
            onmouseout="this.style.background=''">
          <td style="padding:12px 16px;font-weight:600;color:#111827">{s['name']}</td>
          <td style="padding:12px 16px;color:#6b7280">{age_disp}</td>
          <td style="padding:12px 16px;color:#6b7280">{s['patrol']}</td>
          <td style="padding:12px 16px;font-weight:700;color:{bal_color}">{format_currency(bal)}</td>
          <td style="padding:12px 16px;font-size:12px;color:#9ca3af">{parents}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:white;border-radius:12px;border:1px solid #e5e7eb;
                box-shadow:0 1px 3px rgba(0,0,0,.05);overflow:hidden;margin-bottom:16px">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
          <th style="text-align:left;padding:11px 16px;font-size:11px;text-transform:uppercase;
                     letter-spacing:.06em;color:#6b7280;font-weight:600">Name</th>
          <th style="text-align:left;padding:11px 16px;font-size:11px;text-transform:uppercase;
                     letter-spacing:.06em;color:#6b7280;font-weight:600">Age</th>
          <th style="text-align:left;padding:11px 16px;font-size:11px;text-transform:uppercase;
                     letter-spacing:.06em;color:#6b7280;font-weight:600">Patrol</th>
          <th style="text-align:left;padding:11px 16px;font-size:11px;text-transform:uppercase;
                     letter-spacing:.06em;color:#6b7280;font-weight:600">Balance</th>
          <th style="text-align:left;padding:11px 16px;font-size:11px;text-transform:uppercase;
                     letter-spacing:.06em;color:#6b7280;font-weight:600">Parents</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>""", unsafe_allow_html=True)

    # Per-scout action buttons
    section_header("Scout Actions")
    st.markdown(
        "<p style='font-size:13px;color:#6b7280;margin:-8px 0 12px'>View details or export ledger for a scout:</p>",
        unsafe_allow_html=True)

    scout_list = [(int(s["scout_id"]), s["name"]) for _, s in scouts.iterrows()]
    if scout_list:
        n_cols = min(len(scout_list), 4)
        btn_cols = st.columns(n_cols)
        for i, (sid, sname) in enumerate(scout_list):
            with btn_cols[i % n_cols]:
                if st.button(f"👤 {sname}", key=f"view_{sid}", use_container_width=True):
                    goto("scout_detail", scout_id=sid)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: SCOUT DETAIL
# ═════════════════════════════════════════════════════════════════════════════
def page_scout_detail():
    sid   = st.session_state.selected_scout
    scout = fm.get_scout(sid)

    if scout is None:
        st.error("Scout not found.")
        if st.button("← Back"):
            goto("scouts")
        return

    # Back
    if st.button("← Back to Scouts", key="back"):
        goto("scouts")

    bal     = float(scout.get("balance", 0))
    bal_col = "#16a34a" if bal >= 0 else "#dc2626"
    age     = int(scout["age"]) if pd.notna(scout.get("age")) and scout.get("age") else "N/A"
    parents = str(scout.get("parent_names", "") or "").strip() or "N/A"
    patrol  = str(scout.get("patrol", "") or "")
    email   = str(scout.get("email", "") or "").strip() or "N/A"
    initials = "".join(w[0].upper() for w in str(scout["name"]).split()[:2])

    st.markdown(f"""
    <div class="scout-hdr">
      <div class="scout-avatar">{initials}</div>
      <div style="flex:1">
        <div class="scout-name">{scout['name']}</div>
        <div class="scout-meta">
          Age {age} &nbsp;·&nbsp; {patrol} Patrol &nbsp;·&nbsp; {email}
        </div>
        <div class="scout-meta">Parents: {parents}</div>
      </div>
      <div style="text-align:right;flex-shrink:0">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                    color:#6b7280;margin-bottom:4px;font-weight:600">Balance</div>
        <div style="font-size:28px;font-weight:800;color:{bal_col};letter-spacing:-0.02em">{format_currency(bal)}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Edit
    with st.expander("✏️  Edit Scout Info"):
        with st.form(f"edit_{sid}"):
            ec1, ec2 = st.columns(2)
            with ec1:
                new_name    = st.text_input("Name", value=str(scout.get("name", "")))
                new_age     = st.number_input("Age", 0, 25, int(scout.get("age", 0) or 0))
            with ec2:
                pidx = PATROLS.index(patrol) if patrol in PATROLS else 0
                new_patrol  = st.selectbox("Patrol", PATROLS, index=pidx)
                new_parents = st.text_input("Parents", value=str(scout.get("parent_names", "") or ""))
            new_email = st.text_input("Email", value=str(scout.get("email", "") or ""))
            if st.form_submit_button("Save Changes"):
                fm.edit_scout(sid, name=new_name, age=int(new_age),
                              parent_names=new_parents, patrol=new_patrol, email=new_email)
                st.success("Saved!")
                st.rerun()

    # Ledger
    txns = fm.get_scout_transactions(sid)
    h1, h2 = st.columns([5, 1])
    with h1:
        section_header("Transaction History")
    with h2:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        csv = fm.export_scout_ledger(sid)
        if csv:
            st.download_button(
                "⬇ CSV", data=csv,
                file_name=f"ledger_{str(scout['name']).replace(' ', '_')}.csv",
                mime="text/csv", use_container_width=True,
            )

    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No transactions yet</div>
          <div class="empty-sub">This scout has no recorded transactions</div>
        </div>""", unsafe_allow_html=True)
    else:
        sorted_txns = sort_df(txns, f"det_{sid}")
        st.markdown(txn_table_html(sorted_txns, show_scouts=False), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: REGISTER
# ═════════════════════════════════════════════════════════════════════════════
def page_register():
    st.markdown('<h1 class="page-title">Register Transaction</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Record income, expenses, deposits, fees, and transfers</p>',
                unsafe_allow_html=True)

    # Flash message
    if st.session_state.flash:
        kind, msg = st.session_state.flash
        (st.success if kind == "ok" else st.error)(msg)
        st.session_state.flash = None

    rk = st.session_state.reg_key   # key suffix — bumped on submit to reset widgets

    # ── Type + Description + Date + Amount ────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)

    TYPE_LABELS = {
        "EventIncome":    "💵  Event Income",
        "CampoutExpense": "⛺  Campout Expense",
        "EventExpense":   "🎭  Event Expense",
        "Fee":            "📑  Fee",
        "Deposit":        "🏦  Deposit",
        "Transfer":       "🔄  Transfer",
    }

    c1, c2 = st.columns(2)
    with c1:
        txn_type = st.selectbox(
            "Transaction Type *",
            TRANSACTION_TYPES,
            format_func=lambda t: TYPE_LABELS.get(t, t),
            key=f"reg_type_{rk}",
        )
        description = st.text_input("Description *",
                                    placeholder="Brief description…",
                                    key=f"reg_desc_{rk}")
    with c2:
        date   = st.date_input("Date *", value=datetime.today(), key=f"reg_date_{rk}")
        amount = st.number_input("Amount ($) *", min_value=0.01, value=50.0,
                                 step=0.01, format="%.2f", key=f"reg_amt_{rk}")

    st.markdown("---")
    defs = TYPE_DEFAULTS.get(txn_type, {"bank": 0, "scout": 0, "needs_scouts": False})

    # ── Transfer: two scout selectors ─────────────────────────────────────
    if txn_type == "Transfer":
        st.markdown("**Transfer** — moves funds between two scout accounts (no bank change)")
        scout_opts = [(int(s["scout_id"]), s["name"]) for _, s in fm.scouts.iterrows()]
        if len(scout_opts) < 2:
            st.warning("Need at least 2 scouts for a Transfer.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        opt_map = {sid: name for sid, name in scout_opts}
        tc1, tc2 = st.columns(2)
        with tc1:
            from_id = st.selectbox("From Scout *",
                                   [s for s, _ in scout_opts],
                                   format_func=lambda x: opt_map[x],
                                   key=f"reg_from_{rk}")
        with tc2:
            to_opts = [s for s, _ in scout_opts if s != from_id]
            to_id = st.selectbox("To Scout *",
                                 to_opts,
                                 format_func=lambda x: opt_map[x],
                                 key=f"reg_to_{rk}")
        bank_delta  = 0.0
        scout_delta = 0.0
        selected_scouts: list = []

    # ── All other types: bank_delta, scout_delta, multi-scout ─────────────
    else:
        from_id = None
        to_id   = None

        dc1, dc2 = st.columns(2)
        with dc1:
            bank_delta = st.number_input(
                "Bank Delta ($)",
                value=float(round(amount * defs["bank"], 2)),
                step=0.01, format="%.2f",
                help="Positive = money into bank, Negative = out of bank",
                key=f"reg_bd_{rk}",
            )
        with dc2:
            scout_delta = st.number_input(
                "Scout Delta ($ per scout)",
                value=float(round(amount * defs["scout"], 2)),
                step=0.01, format="%.2f",
                help="Applied to each selected scout's balance",
                key=f"reg_sd_{rk}",
            )

        # Multi-scout selector
        needs = defs["needs_scouts"]
        st.markdown(f"**Scouts** {'*(required)*' if needs else '*(optional)*'}")

        scout_opts = [(int(s["scout_id"]), s["name"]) for _, s in fm.scouts.iterrows()]
        if scout_opts:
            opt_map = {sid: name for sid, name in scout_opts}

            # Search filter
            sf1, sf2, sf3 = st.columns([3, 1, 1])
            with sf1:
                search_scouts = st.text_input("", placeholder="Filter scouts…",
                                              label_visibility="collapsed",
                                              key=f"reg_sf_{rk}")
            filtered_opts = [(sid, nm) for sid, nm in scout_opts
                             if not search_scouts or search_scouts.lower() in nm.lower()]

            with sf2:
                if st.button("Select All", key=f"reg_all_{rk}", use_container_width=True):
                    st.session_state[f"reg_ms_{rk}"] = [s for s, _ in filtered_opts]
                    st.rerun()
            with sf3:
                if st.button("Clear", key=f"reg_clr_{rk}", use_container_width=True):
                    st.session_state[f"reg_ms_{rk}"] = []
                    st.rerun()

            selected_scouts = st.multiselect(
                "scouts_select",
                options=[s for s, _ in filtered_opts],
                format_func=lambda x: opt_map.get(x, str(x)),
                label_visibility="collapsed",
                key=f"reg_ms_{rk}",
            )
        else:
            st.info("No scouts registered yet.")
            selected_scouts = []

    # Effect preview
    if txn_type != "Transfer":
        parts = []
        if bank_delta > 0:
            parts.append(f"Bank **+{format_currency(bank_delta)}**")
        elif bank_delta < 0:
            parts.append(f"Bank **{format_currency(bank_delta)}**")
        if scout_delta != 0 and selected_scouts:
            n = len(selected_scouts)
            sign = "+" if scout_delta > 0 else ""
            parts.append(f"{n} scout{'s' if n != 1 else ''} **{sign}{format_currency(scout_delta)}** each")
        if parts:
            st.info("Effect: " + " · ".join(parts))

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Submit ─────────────────────────────────────────────────────────────
    if st.button("✓  Submit Transaction", use_container_width=True, key=f"reg_submit_{rk}"):
        # Validation
        if not str(description).strip():
            st.session_state.flash = ("err", "Description is required.")
            st.rerun()
        elif txn_type == "Transfer" and (from_id is None or to_id is None):
            st.session_state.flash = ("err", "Both scouts required for Transfer.")
            st.rerun()
        elif txn_type in ("Deposit", "Fee") and not selected_scouts:
            st.session_state.flash = ("err", f"{txn_type} requires at least one scout.")
            st.rerun()
        else:
            txn_id = fm.add_transaction(
                date=date,
                description=str(description).strip(),
                transaction_type=txn_type,
                amount=float(amount),
                bank_delta=float(bank_delta),
                scout_delta=float(scout_delta),
                scout_ids=selected_scouts if txn_type != "Transfer" else [],
                from_scout_id=from_id if txn_type == "Transfer" else None,
                to_scout_id=to_id if txn_type == "Transfer" else None,
            )
            st.session_state.flash = ("ok", f"Transaction **{txn_id}** recorded successfully!")
            st.session_state.reg_key += 1   # reset form widgets
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: REPORTS
# ═════════════════════════════════════════════════════════════════════════════
def page_reports():
    st.markdown('<h1 class="page-title">Reports</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Filter, analyse, and export transactions</p>',
                unsafe_allow_html=True)

    txns = fm.get_all_transactions()

    with st.expander("🔍  Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            start = st.date_input("From", value=datetime.today() - timedelta(days=90))
        with fc2:
            end = st.date_input("To", value=datetime.today())
        with fc3:
            type_filter = st.multiselect("Type", TRANSACTION_TYPES,
                                         format_func=lambda t: TYPE_META.get(t, ("","","",t))[2])
        with fc4:
            sl = scout_lookup()
            scout_filter = st.multiselect("Scout",
                                          list(sl.keys()),
                                          format_func=lambda x: sl.get(x, str(x)))

    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No transactions yet</div>
        </div>""", unsafe_allow_html=True)
        return

    filtered = txns.copy()
    filtered = filtered[filtered["date"] >= pd.to_datetime(start)]
    filtered = filtered[filtered["date"] <= pd.to_datetime(end)]
    if type_filter:
        filtered = filtered[filtered["transaction_type"].isin(type_filter)]
    if scout_filter:
        def _has_scout(row):
            ids = ScoutFinanceManager._parse_ids(row.get("scout_ids", ""))
            fi  = ScoutFinanceManager._safe_int(row.get("from_scout_id"))
            ti  = ScoutFinanceManager._safe_int(row.get("to_scout_id"))
            all_ids = ids + ([fi] if fi else []) + ([ti] if ti else [])
            return any(s in all_ids for s in scout_filter)
        filtered = filtered[filtered.apply(_has_scout, axis=1)]

    # Summary cards
    bank_net  = float(filtered["bank_delta"].sum()) if "bank_delta" in filtered.columns else 0
    scout_net = float(filtered["scout_delta"].sum()) if "scout_delta" in filtered.columns else 0
    sm1, sm2, sm3 = st.columns(3)
    with sm1:
        st.markdown(stat_card("📋", "Transactions", str(len(filtered))), unsafe_allow_html=True)
    with sm2:
        st.markdown(stat_card("🏦", "Net Bank Impact", format_currency(bank_net),
                               "green" if bank_net >= 0 else "red"), unsafe_allow_html=True)
    with sm3:
        st.markdown(stat_card("👤", "Net Scout Impact", format_currency(scout_net),
                               "green" if scout_net >= 0 else "red"), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    ec, _ = st.columns([1, 3])
    with ec:
        csv_export = filtered.to_csv(index=False)
        st.download_button("⬇ Export CSV", data=csv_export,
                           file_name="scout_report.csv", mime="text/csv",
                           use_container_width=True)

    section_header("Filtered Transactions")
    if filtered.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">🔍</div>
          <div class="empty-title">No matches</div>
          <div class="empty-sub">Try adjusting your filters</div>
        </div>""", unsafe_allow_html=True)
    else:
        sorted_filtered = sort_df(filtered, "rep")
        st.markdown(txn_table_html(sorted_filtered, scout_lookup=sl), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═════════════════════════════════════════════════════════════════════════════
_page = st.session_state.page

if _page == "dashboard":
    page_dashboard()
elif _page == "scouts":
    page_scouts()
elif _page == "scout_detail":
    if st.session_state.selected_scout is not None:
        page_scout_detail()
    else:
        page_scouts()
elif _page == "register":
    page_register()
elif _page == "reports":
    page_reports()
else:
    page_dashboard()
