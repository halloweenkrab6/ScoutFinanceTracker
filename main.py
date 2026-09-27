import base64
from pathlib import Path

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from data_manager import ScoutFinanceManager, TRANSACTION_TYPES, LEDGER_TYPES, PATROLS
from utils import (
    format_currency, badge_html, txn_table_html,
    create_balance_chart, create_type_breakdown,
    TYPE_META,
)
from styles import apply_styles, SIDEBAR_TEXT

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
    "selected_event": None,
    "evt_ver": 0,
    "scout_ver": 0,
    "reg_key": 0,
    "flash": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.fm is None:
    st.session_state.fm = ScoutFinanceManager()

fm: ScoutFinanceManager = st.session_state.fm


@st.cache_data
def logo_data_uri():
    data = (Path(__file__).parent / "assets" / "logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


# ── Navigation helpers ────────────────────────────────────────────────────────
def goto(page, scout_id=None, event_id=None):
    st.session_state.page = page
    st.session_state.selected_scout = scout_id
    st.session_state.selected_event = event_id
    st.rerun()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
_TOP_PAGE = {
    "dashboard": "dashboard",
    "scouts": "scouts",
    "scout_detail": "scouts",
    "events": "events",
    "event_detail": "events",
    "transactions": "transactions",
    "reports": "reports",
}

NAV_ITEMS = [
    ("dashboard", "📊  Dashboard"),
    ("scouts",    "👥  Scouts"),
    ("events",    "🏕️  Events"),
    ("transactions", "💵  Transactions"),
    ("reports",   "📈  Reports"),
]
NAV_LABELS = [lbl for _, lbl in NAV_ITEMS]
NAV_MAP    = {lbl: pid for pid, lbl in NAV_ITEMS}

current_top  = _TOP_PAGE.get(st.session_state.page, "dashboard")
current_lbl  = next(lbl for pid, lbl in NAV_ITEMS if pid == current_top)
current_idx  = NAV_LABELS.index(current_lbl)

with st.sidebar:
    st.markdown(f"""
    <div style="padding:24px 20px 18px;border-bottom:1px solid {SIDEBAR_TEXT}20">
      <img src="{logo_data_uri()}" alt="Scout Finance Tracker logo"
           style="display:block;width:100%;max-width:180px;height:auto;margin:0 auto 12px">
      <div style="font-size:15px;font-weight:700;color:{SIDEBAR_TEXT};letter-spacing:-0.02em">Scout Finance</div>
      <div style="font-size:11px;color:{SIDEBAR_TEXT};margin-top:2px;letter-spacing:.02em">TROOP TRACKER</div>
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
    <div style="margin-top:auto;padding:16px 12px 22px;border-top:1px solid {SIDEBAR_TEXT}20">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;
                  color:{SIDEBAR_TEXT};margin-bottom:10px;font-weight:600">Quick View</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:7px">
        <span style="font-size:12px;color:{SIDEBAR_TEXT}">Bank</span>
        <span style="font-size:13px;font-weight:700;color:{'#4ade80' if bank>=0 else '#f87171'}">{format_currency(bank)}</span>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span style="font-size:12px;color:{SIDEBAR_TEXT}">Scouts</span>
        <span style="font-size:13px;font-weight:600;color:{SIDEBAR_TEXT}">{scout_cnt} members</span>
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


def chart_placeholder(text):
    """Stands in for a chart until there's enough data; same height as the charts."""
    return (f'<div style="height:210px;display:flex;align-items:center;justify-content:center;'
            f'color:#9ca3af;font-size:14px">{text}</div>')


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
        ("💰", "Troop Gross Assets",     format_currency(gross), ""),
        ("🏦", "Bank Balance",          format_currency(bank),  "green" if bank >= 0 else "red"),
        ("⚜️", "Troop Account",         format_currency(troop), "green" if troop >= 0 else "red"),
        ("👤", "Scout Balances (+)",    format_currency(pos),   "green"),
        ("⚠️", "Scout Balances (−)",    format_currency(neg),   "red"),
    ]
    for col, (icon, label, val, color) in zip(cols, cards):
        with col:
            st.markdown(stat_card(icon, label, val, color), unsafe_allow_html=True)

    # Charts
    txns = fm.get_ledger()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ch1, ch2 = st.columns([3, 2])
    with ch1:
        st.markdown('<div class="card"><div class="card-title">Bank Balance Timeline</div>',
                    unsafe_allow_html=True)
        if len(txns) >= 2:
            st.plotly_chart(create_balance_chart(txns), width="stretch",
                            config={"displayModeBar": False})
        else:
            st.markdown(chart_placeholder("No timeline yet"), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with ch2:
        st.markdown('<div class="card"><div class="card-title">By Transaction Type</div>',
                    unsafe_allow_html=True)
        if (txns["amount"] != 0).any():
            st.plotly_chart(create_type_breakdown(txns), width="stretch",
                            config={"displayModeBar": False})
        else:
            st.markdown(chart_placeholder("No transactions yet"), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Full ledger
    section_header("Full Ledger")
    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No activity yet</div>
          <div class="empty-sub">Create an event or record a transaction to get started</div>
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
                parent_name  = st.text_input("Parent / Guardian")
                parent_phone = st.text_input("Parent Phone")
                parent_email = st.text_input("Parent Email")
            st.caption("More parents can be added from the scout's page.")
            if st.form_submit_button("Add Scout", width="stretch"):
                if not name.strip():
                    st.error("Name is required.")
                else:
                    parents = ([{"name": parent_name.strip(), "phone": parent_phone.strip(),
                                 "email": parent_email.strip()}]
                               if parent_name.strip() else [])
                    sid = fm.add_scout(name.strip(), int(age), patrol, email.strip(), parents)
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
    search = st.text_input("Search scouts", placeholder="🔍  Search by name or patrol…",
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
    parent_names = fm.get_parent_names()
    rows_html = ""
    for _, s in scouts.iterrows():
        sid = int(s["scout_id"])
        bal = float(s["balance"])
        bal_color = "#16a34a" if bal >= 0 else "#dc2626"
        age_disp  = int(s["age"]) if pd.notna(s.get("age")) and s.get("age") else "—"
        parents   = parent_names.get(sid, "—")
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
                if st.button(f"👤 {sname}", key=f"view_{sid}", width="stretch"):
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
    show_flash()

    bal     = float(scout.get("balance", 0))
    bal_col = "#16a34a" if bal >= 0 else "#dc2626"
    age     = int(scout["age"]) if pd.notna(scout.get("age")) and scout.get("age") else "N/A"
    parents = fm.get_parents(sid)
    patrol  = str(scout.get("patrol", "") or "")
    email   = str(scout.get("email", "") or "").strip() or "N/A"
    initials = "".join(w[0].upper() for w in str(scout["name"]).split()[:2])
    parents_html = "".join(
        '<div class="scout-meta">Parent: '
        + " &nbsp;·&nbsp; ".join(v for v in (p["name"], p["phone"], p["email"]) if v)
        + "</div>"
        for _, p in parents.iterrows()
    ) or '<div class="scout-meta">Parents: N/A</div>'

    st.markdown(f"""
    <div class="scout-hdr">
      <div class="scout-avatar">{initials}</div>
      <div style="flex:1">
        <div class="scout-name">{scout['name']}</div>
        <div class="scout-meta">
          Age {age} &nbsp;·&nbsp; {patrol} Patrol &nbsp;·&nbsp; {email}
        </div>
        {parents_html}
      </div>
      <div style="text-align:right;flex-shrink:0">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                    color:#6b7280;margin-bottom:4px;font-weight:600">Balance</div>
        <div style="font-size:28px;font-weight:800;color:{bal_col};letter-spacing:-0.02em">{format_currency(bal)}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Edit
    with st.expander("✏️  Edit Scout Info"):
        with st.form(f"edit_{sid}_{st.session_state.scout_ver}"):
            ec1, ec2 = st.columns(2)
            with ec1:
                new_name    = st.text_input("Name", value=str(scout.get("name", "")))
                new_age     = st.number_input("Age", 0, 25, int(scout.get("age", 0) or 0))
            with ec2:
                pidx = PATROLS.index(patrol) if patrol in PATROLS else 0
                new_patrol  = st.selectbox("Patrol", PATROLS, index=pidx)
                new_email   = st.text_input("Email", value=str(scout.get("email", "") or ""))

            st.markdown("**Parents / Guardians**")
            st.caption("Add a parent in the empty bottom row. Tick Remove to delete one, then save.")
            edited_parents = st.data_editor(
                pd.DataFrame({"Parent": parents["name"], "Phone": parents["phone"],
                              "Email": parents["email"], "Remove": False}),
                num_rows="dynamic", hide_index=True, width="stretch",
                column_config={
                    "Parent": st.column_config.TextColumn(required=True),
                    "Phone":  st.column_config.TextColumn(),
                    "Email":  st.column_config.TextColumn(),
                    "Remove": st.column_config.CheckboxColumn(default=False, width="small"),
                },
            )
            if st.form_submit_button("Save Changes"):
                rows = [{"name": _txt(r["Parent"]), "phone": _txt(r["Phone"]), "email": _txt(r["Email"])}
                        for _, r in edited_parents.iterrows() if r["Remove"] is not True]
                if any(not r["name"] and (r["phone"] or r["email"]) for r in rows):
                    st.error("Every parent needs a name.")
                else:
                    fm.edit_scout(sid, name=new_name, age=int(new_age),
                                  patrol=new_patrol, email=new_email)
                    fm.set_parents(sid, [r for r in rows if r["name"]])
                    st.session_state.flash = ("ok", "Saved!")
                    st.session_state.scout_ver += 1
                    st.rerun()

    # Ledger
    txns = fm.get_ledger([sid])
    h1, h2 = st.columns([5, 1])
    with h1:
        section_header("Account History")
    with h2:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        csv = fm.export_scout_ledger(sid)
        if csv:
            st.download_button(
                "⬇ CSV", data=csv,
                file_name=f"ledger_{str(scout['name']).replace(' ', '_')}.csv",
                mime="text/csv", width="stretch",
            )

    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No activity yet</div>
          <div class="empty-sub">This scout has no transactions or event charges</div>
        </div>""", unsafe_allow_html=True)
    else:
        sorted_txns = sort_df(txns, f"det_{sid}")
        st.markdown(txn_table_html(sorted_txns, show_scouts=False), unsafe_allow_html=True)


def show_flash():
    if st.session_state.flash:
        kind, msg = st.session_state.flash
        {"ok": st.success, "warn": st.warning}.get(kind, st.error)(msg)
        st.session_state.flash = None


def _num(v, default=0.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return default if pd.isna(f) else f


def _txt(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: EVENTS
# ═════════════════════════════════════════════════════════════════════════════
def page_events():
    st.markdown('<h1 class="page-title">Events</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Campouts and activities, with per-scout charges</p>',
                unsafe_allow_html=True)
    show_flash()

    sl = scout_lookup()
    summaries = fm.get_event_summaries()

    with st.expander("➕  New Event", expanded=summaries.empty):
        with st.form("new_event", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Event Name *", placeholder="e.g. October Campout")
            with c2:
                date = st.date_input("Date", value=datetime.today())
            everyone = st.checkbox("All scouts are attending", value=True)
            attendees = st.multiselect("…or pick attendees", list(sl.keys()),
                                       format_func=lambda x: sl.get(x, str(x)))
            if st.form_submit_button("Create Event", width="stretch"):
                if not name.strip():
                    st.error("Event name is required.")
                else:
                    ids = list(sl.keys()) if everyone else attendees
                    eid = fm.create_event(name.strip(), date, attendee_ids=ids)
                    st.session_state.flash = ("ok", "Event created. Add its expenses below.")
                    goto("event_detail", event_id=eid)

    if summaries.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">🏕️</div>
          <div class="empty-title">No events yet</div>
          <div class="empty-sub">Use the form above to create your first event</div>
        </div>""", unsafe_allow_html=True)
        return

    rows_html = ""
    for _, ev in summaries.iterrows():
        net_color = "#16a34a" if ev["net"] >= 0 else "#dc2626"
        date_str = ev["date"].strftime("%b %d, %Y") if pd.notna(ev["date"]) else "—"
        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6">
          <td style="padding:12px 16px;color:#6b7280;white-space:nowrap">{date_str}</td>
          <td style="padding:12px 16px;font-weight:600;color:#111827">{ev['name']}</td>
          <td style="padding:12px 16px;color:#6b7280">{ev['attendees']}</td>
          <td style="padding:12px 16px;text-align:right">{format_currency(ev['charged'])}</td>
          <td style="padding:12px 16px;text-align:right">{format_currency(ev['troop_paid'])}</td>
          <td style="padding:12px 16px;text-align:right;font-weight:700;color:{net_color}">{format_currency(ev['net'])}</td>
        </tr>"""
    th = ("padding:11px 16px;font-size:11px;text-transform:uppercase;"
          "letter-spacing:.06em;color:#6b7280;font-weight:600;")
    st.markdown(f"""
    <div style="background:white;border-radius:12px;border:1px solid #e5e7eb;
                box-shadow:0 1px 3px rgba(0,0,0,.05);overflow:hidden;margin-bottom:16px">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
          <th style="{th}text-align:left">Date</th>
          <th style="{th}text-align:left">Event</th>
          <th style="{th}text-align:left">Scouts</th>
          <th style="{th}text-align:right">Charged to Scouts</th>
          <th style="{th}text-align:right">Paid by Troop</th>
          <th style="{th}text-align:right">Net</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>""", unsafe_allow_html=True)

    section_header("Open an Event")
    n_cols = min(len(summaries), 4)
    btn_cols = st.columns(n_cols)
    for i, (_, ev) in enumerate(summaries.iterrows()):
        with btn_cols[i % n_cols]:
            if st.button(f"🏕️ {ev['name']}", key=f"open_{ev['event_id']}", width="stretch"):
                goto("event_detail", event_id=ev["event_id"])


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: EVENT DETAIL
# ═════════════════════════════════════════════════════════════════════════════
def page_event_detail():
    eid = st.session_state.selected_event
    ev  = fm.get_event(eid)
    if ev is None:
        st.error("Event not found.")
        if st.button("← Back"):
            goto("events")
        return

    if st.button("← Back to Events", key="back"):
        goto("events")
    show_flash()

    sl       = scout_lookup()
    expenses = fm.get_event_expenses(eid)
    charges  = fm.get_event_charges(eid)
    attendees = [s for s in ev["attendee_ids"] if s in sl]

    charged_total = float(charges["amount"].sum())
    paid_total    = float(expenses["troop_paid"].sum())
    net           = charged_total - paid_total

    st.markdown(f'<h1 class="page-title">{ev["name"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-subtitle">{pd.to_datetime(ev["date"]).strftime("%B %d, %Y")}</p>',
                unsafe_allow_html=True)
    cols = st.columns(4)
    for col, card in zip(cols, [
        ("👥", "Scouts Attending", str(len(attendees)), ""),
        ("🧾", "Charged to Scouts", format_currency(charged_total), ""),
        ("🏦", "Paid by Troop", format_currency(paid_total), ""),
        ("⚖️", "Net", format_currency(net), "green" if net >= 0 else "red"),
    ]):
        with col:
            st.markdown(stat_card(*card), unsafe_allow_html=True)

    # Labels for the grid columns and the custom-amount dropdowns
    exp_label, used = {}, set()
    for _, x in expenses.iterrows():
        base = x["name"] or x["expense_id"]
        label, n = base, 2
        while label in used or label in ("Scout", "scout_id"):
            label, n = f"{base} ({n})", n + 1
        used.add(label)
        exp_label[x["expense_id"]] = label
    label_exp = {v: k for k, v in exp_label.items()}
    scout_label = {sid: f"{sl[sid]} (#{sid})" for sid in attendees}
    label_scout = {v: k for k, v in scout_label.items()}

    ver = st.session_state.evt_ver
    with st.form(f"evt_form_{eid}_{ver}"):
        section_header("Details")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Event Name", value=ev["name"])
        with c2:
            date = st.date_input("Date", value=pd.to_datetime(ev["date"]).date())
        notes = st.text_area("Notes", value=ev["notes"], height=68)
        new_attendees = st.multiselect("Scouts attending", list(sl.keys()), default=attendees,
                                       format_func=lambda x: sl.get(x, str(x)))

        section_header("Expenses")
        st.caption("Price per scout is what each charged scout pays. Troop paid is what the "
                   "troop actually spent (optional). New expenses and newly added scouts are "
                   "charged automatically when Charge all is ticked.")
        exp_df = pd.DataFrame({
            "expense_id":      expenses["expense_id"],
            "Expense":         expenses["name"],
            "Price per scout": expenses["unit_price"],
            "Troop paid":      expenses["troop_paid"],
            "Charge all":      expenses["charge_all"],
        })
        edited_exp = st.data_editor(
            exp_df, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["Expense", "Price per scout", "Troop paid", "Charge all"],
            column_config={
                "Expense":         st.column_config.TextColumn(required=True),
                "Price per scout": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="$%.2f", default=0.0),
                "Troop paid":      st.column_config.NumberColumn(min_value=0.0, step=0.01, format="$%.2f", default=0.0),
                "Charge all":      st.column_config.CheckboxColumn(default=True),
            },
            key=f"evt_exp_{eid}_{ver}",
        )

        section_header("Who's Charged")
        edited_grid = edited_ov = None
        if attendees and not expenses.empty:
            st.caption("Tick each expense a scout should pay for. Scouts or expenses added "
                       "above show up here after you save.")
            pairs = set(zip(charges["scout_id"], charges["expense_id"]))
            grid = pd.DataFrame({"scout_id": attendees, "Scout": [sl[s] for s in attendees]})
            for xid, label in exp_label.items():
                grid[label] = [(s, xid) in pairs for s in attendees]
            edited_grid = st.data_editor(
                grid, hide_index=True, width="stretch", disabled=["Scout"],
                column_order=["Scout"] + list(exp_label.values()),
                column_config={
                    label: st.column_config.CheckboxColumn(
                        label, help=f"{format_currency(expenses.loc[expenses['expense_id'] == xid, 'unit_price'].iloc[0])} per scout")
                    for xid, label in exp_label.items()
                },
                key=f"evt_grid_{eid}_{ver}",
            )

            with st.expander("Custom amounts"):
                st.caption("Charge a scout a different amount for one expense, such as a "
                           "discount or a partial share. Only applies where that box is ticked.")
                ov = charges[charges["amount_override"].notna() & charges["scout_id"].isin(attendees)]
                # Explicit dtypes: an empty table would otherwise default every
                # column to float and discard the scout/expense picked in a new row.
                ov_df = pd.DataFrame({
                    "Scout":   pd.Series([scout_label[s] for s in ov["scout_id"]], dtype=object),
                    "Expense": pd.Series([exp_label[x] for x in ov["expense_id"]], dtype=object),
                    "Amount":  pd.Series(ov["amount_override"].tolist(), dtype=float),
                })
                edited_ov = st.data_editor(
                    ov_df, num_rows="dynamic", hide_index=True, width="stretch",
                    column_config={
                        "Scout":   st.column_config.SelectboxColumn(options=list(scout_label.values()), required=True),
                        "Expense": st.column_config.SelectboxColumn(options=list(exp_label.values()), required=True),
                        "Amount":  st.column_config.NumberColumn(min_value=0.0, step=0.01, format="$%.2f", required=True),
                    },
                    key=f"evt_ov_{eid}_{ver}",
                )
        else:
            st.info("Add scouts and at least one expense above, then save. "
                    "The charge grid will appear here.")

        submitted = st.form_submit_button("✓  Save Event", width="stretch")

    if submitted:
        exp_rows, errors = [], []
        for _, r in edited_exp.iterrows():
            nm = _txt(r["Expense"])
            if not nm:
                if _num(r["Price per scout"]) or _num(r["Troop paid"]):
                    errors.append("Every expense needs a name.")
                continue
            xid = _txt(r["expense_id"])
            exp_rows.append({
                "expense_id":  xid or None,
                "name":        nm,
                "unit_price":  _num(r["Price per scout"]),
                "troop_paid":  _num(r["Troop paid"]),
                "charge_all":  True if pd.isna(r["Charge all"]) else bool(r["Charge all"]),
            })

        charged = set()
        if edited_grid is not None:
            for _, r in edited_grid.iterrows():
                for label, xid in label_exp.items():
                    if bool(r[label]):
                        charged.add((int(r["scout_id"]), xid))

        overrides = {}
        if edited_ov is not None:
            for _, r in edited_ov.iterrows():
                s, x = label_scout.get(_txt(r["Scout"])), label_exp.get(_txt(r["Expense"]))
                if s is None or x is None or pd.isna(r["Amount"]):
                    continue
                overrides[(s, x)] = float(r["Amount"])

        if not _txt(name):
            errors.append("Event name is required.")
        if errors:
            st.error(" ".join(dict.fromkeys(errors)))
        else:
            dropped = fm.save_event(eid, _txt(name), date, _txt(notes), new_attendees,
                                    exp_rows, charged, overrides)
            if dropped:
                names = ", ".join(f"{sl.get(s, s)} / {exp_label.get(x, x)}" for s, x in dropped)
                st.session_state.flash = ("warn", f"Saved. Ignored custom amounts for unticked "
                                                  f"charges: {names}")
            else:
                st.session_state.flash = ("ok", "Event saved.")
            st.session_state.evt_ver += 1
            st.rerun()

    # Per-scout totals (saved state)
    if not charges.empty:
        section_header("Per-Scout Totals")
        per = charges.groupby("scout_id")["amount"].sum()
        rows_html = "".join(f"""
        <tr style="border-bottom:1px solid #f3f4f6">
          <td style="padding:10px 16px;color:#111827">{sl.get(s, s)}</td>
          <td style="padding:10px 16px;text-align:right;font-weight:700">{format_currency(per.get(s, 0.0))}</td>
        </tr>""" for s in attendees)
        st.markdown(f"""
        <div style="background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;max-width:480px">
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <tbody>{rows_html}</tbody>
          <tfoot><tr style="background:#f9fafb;border-top:2px solid #e5e7eb">
            <td style="padding:10px 16px;font-weight:700">Total</td>
            <td style="padding:10px 16px;text-align:right;font-weight:800">{format_currency(charged_total)}</td>
          </tr></tfoot>
        </table>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    with st.expander("🗑️  Delete this event"):
        st.caption("Removes the event and all of its charges and troop payments. This can't be undone.")
        confirm = st.checkbox("Yes, delete this event", key=f"del_evt_{eid}")
        if st.button("Delete Event", disabled=not confirm, key=f"del_evt_btn_{eid}"):
            fm.delete_event(eid)
            st.session_state.flash = ("ok", f"Deleted event **{ev['name']}**.")
            goto("events")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ═════════════════════════════════════════════════════════════════════════════
def page_transactions():
    st.markdown('<h1 class="page-title">Transactions</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Money moving directly between a scout and the troop</p>',
                unsafe_allow_html=True)
    show_flash()

    sl = scout_lookup()
    if not sl:
        st.info("Add a scout first, on the Scouts page.")
        return

    TYPE_LABELS = {
        "Deposit": "🏦  Deposit (scout pays the troop)",
        "Refund":  "↩️  Refund (troop pays the scout)",
    }

    rk = st.session_state.reg_key
    with st.form(f"txn_form_{rk}"):
        c1, c2 = st.columns(2)
        with c1:
            scout_id = st.selectbox("Scout *", list(sl.keys()), format_func=lambda x: sl.get(x, str(x)))
        with c2:
            txn_type = st.radio("Type *", TRANSACTION_TYPES, format_func=TYPE_LABELS.get, horizontal=True)
        c3, c4 = st.columns(2)
        with c3:
            amount = st.number_input("Amount ($) *", min_value=0.01, value=50.0, step=0.01, format="%.2f")
        with c4:
            date = st.date_input("Date", value=datetime.today())
        description = st.text_input("Description", placeholder="e.g. Check #1042, cash at meeting…")

        if st.form_submit_button("✓  Record Transaction", width="stretch"):
            txn_id = fm.add_transaction(date, txn_type, scout_id, float(amount), description.strip())
            st.session_state.flash = ("ok", f"Transaction **{txn_id}** recorded.")
            st.session_state.reg_key += 1   # bumping the key resets the form
            st.rerun()

    ledger = fm.get_ledger()
    txns = ledger[ledger["transaction_type"].isin(TRANSACTION_TYPES)]
    section_header("Recent Transactions")
    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">💵</div>
          <div class="empty-title">No transactions yet</div>
        </div>""", unsafe_allow_html=True)
        return
    st.markdown(txn_table_html(txns, scout_lookup=sl), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    with st.expander("🗑️  Delete a transaction"):
        labels = {
            r["transaction_id"]: f"{r['transaction_id']} · {r['date']:%b %d, %Y} · "
                                 f"{sl.get(int(r['scout_ids']), '?')} · {format_currency(r['amount'])}"
            for _, r in txns.iterrows()
        }
        target = st.selectbox("Transaction", list(labels), format_func=labels.get)
        confirm = st.checkbox("Yes, delete it", key=f"del_txn_{rk}")
        if st.button("Delete Transaction", disabled=not confirm):
            fm.delete_transaction(target)
            st.session_state.flash = ("ok", f"Deleted **{target}**.")
            st.session_state.reg_key += 1
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: REPORTS
# ═════════════════════════════════════════════════════════════════════════════
def page_reports():
    st.markdown('<h1 class="page-title">Reports</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Filter, analyse, and export activity</p>',
                unsafe_allow_html=True)

    with st.expander("🔍  Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            start = st.date_input("From", value=datetime.today() - timedelta(days=90))
        with fc2:
            end = st.date_input("To", value=datetime.today())
        with fc3:
            type_filter = st.multiselect("Type", LEDGER_TYPES,
                                         format_func=lambda t: TYPE_META.get(t, ("", "", t))[2])
        with fc4:
            sl = scout_lookup()
            scout_filter = st.multiselect("Scout",
                                          list(sl.keys()),
                                          format_func=lambda x: sl.get(x, str(x)))

    txns = fm.get_ledger(scout_filter or None)
    if txns.empty:
        st.markdown("""
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No activity yet</div>
        </div>""", unsafe_allow_html=True)
        return

    filtered = txns[(txns["date"] >= pd.to_datetime(start)) & (txns["date"] <= pd.to_datetime(end))]
    if type_filter:
        filtered = filtered[filtered["transaction_type"].isin(type_filter)]

    # Summary cards
    bank_net  = float(filtered["bank_delta"].sum()) if "bank_delta" in filtered.columns else 0
    scout_net = float(filtered["scout_delta"].sum()) if "scout_delta" in filtered.columns else 0
    sm1, sm2, sm3 = st.columns(3)
    with sm1:
        st.markdown(stat_card("📋", "Entries", str(len(filtered))), unsafe_allow_html=True)
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
                           width="stretch")

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
elif _page == "events":
    page_events()
elif _page == "event_detail":
    if st.session_state.selected_event is not None:
        page_event_detail()
    else:
        page_events()
elif _page == "transactions":
    page_transactions()
elif _page == "reports":
    page_reports()
else:
    page_dashboard()
