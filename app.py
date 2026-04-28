import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from src.calculator import calculate
from src.counties import COUNTY_RATES

# ── Data persistence ─────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
SAVE_FILE = DATA_DIR / "saved_data.json"
CUSTOM_FILE = DATA_DIR / "custom_sources.json"

DEFAULT_INCOME_SOURCES = ["Uber", "Empower", "Square", "Lyft", "FT Work", "PT Work", "Other"]
DEFAULT_EXPENSE_CATEGORIES = ["Subscription", "Other"]
MONTH_NAMES = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]


def load_custom_sources():
    if CUSTOM_FILE.exists():
        try:
            return json.loads(CUSTOM_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {"income_sources": list(DEFAULT_INCOME_SOURCES), "expense_categories": list(DEFAULT_EXPENSE_CATEGORIES)}


def save_custom_sources(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_FILE.write_text(json.dumps(data, indent=2))


def load_saved_data():
    if SAVE_FILE.exists():
        try:
            return json.loads(SAVE_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_data(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_saved_data()
    date_key = datetime.now().strftime("%Y-%m-%d")
    existing[date_key] = {
        "inputs": data["inputs"],
        "saved_at": datetime.now().isoformat(),
    }
    if len(existing) > 50:
        keys = sorted(existing.keys())
        for k in keys[:-50]:
            del existing[k]
    SAVE_FILE.write_text(json.dumps(existing, indent=2))


CUSTOM = load_custom_sources()
SAVED = load_saved_data()

# ── Session state init ────────────────────────────────────────────
if "income_entries" not in st.session_state:
    st.session_state.income_entries = []
if "expense_entries" not in st.session_state:
    st.session_state.expense_entries = []
if "current_month" not in st.session_state:
    st.session_state.current_month = None  # None = annual mode
if "monthly_data" not in st.session_state:
    st.session_state.monthly_data = {i: {"income": [], "expenses": []} for i in range(12)}

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(page_title="1099 Tax Calculator", page_icon="🧮", layout="wide")

# ── Custom CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
:root { --navy: #1A1A2E; --teal: #0D7377; --teal-light: #14A3A8; --light-bg: #F7F9FC; }
.stApp { background-color: var(--light-bg); }
.card { background: #fff; border-radius: 12px; padding: 1.2rem 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 .5rem; color: var(--navy); font-size: 1rem; text-transform: uppercase; letter-spacing: .04em; }
.card .value { font-size: 1.8rem; font-weight: 700; color: var(--teal); }
.card .sub { font-size: .85rem; color: #6b7280; }
.header-bar { background: var(--navy); padding: 1.5rem 2rem; border-radius: 0 0 16px 16px; margin-bottom: 1.5rem; }
.header-bar h1 { color: #fff; margin: 0; }
.header-bar p { color: #a5b4c8; margin: .25rem 0 0; }
.section-title { color: var(--navy); font-size: 1.15rem; font-weight: 700; margin: 1.5rem 0 .75rem; border-left: 4px solid var(--teal); padding-left: .5rem; }
.step-row { display: flex; justify-content: space-between; padding: .35rem 0; border-bottom: 1px solid #f0f0f0; font-size: .92rem; }
.step-row:last-child { border-bottom: none; }
.step-label { color: #555; }
.step-value { font-weight: 600; color: var(--navy); }
.neg { color: #dc2626; }
.pos { color: #16a34a; }
.disclaimer { background: #fef3c7; border-left: 4px solid #f59e0b; padding: .75rem 1rem; border-radius: 8px; font-size: .85rem; color: #92400e; margin-top: 2rem; }
.income-card { border-left: 4px solid #16a34a; }
.expense-card { border-left: 4px solid #dc2626; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────
st.markdown("""<div class="header-bar"><h1>🧮 1099 / W-2 Tax Calculator</h1>
<p>Track multiple income sources & expenses — estimate your federal, state & local taxes</p></div>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    last_saved = SAVED.get(sorted(SAVED.keys())[-1], {}) if SAVED else {}
    last_inputs = last_saved.get("inputs", {}) if last_saved else {}
    tax_year = st.selectbox("Tax Year", [2025, 2024], index=[2025, 2024].index(last_inputs.get("tax_year", 2025)))
    sl_interest = st.number_input("Student loan interest paid/year ($)", min_value=0, max_value=10000, value=last_inputs.get("sl_interest", 2500), step=100)
    county = st.selectbox("Maryland County", list(COUNTY_RATES.keys()), index=list(COUNTY_RATES.keys()).index(last_inputs.get("county", "Montgomery")))
    st.caption(f"Local tax rate: {COUNTY_RATES[county]*100:.2f}%")

    st.markdown("---")
    month_mode = st.selectbox("Entry Mode", ["Annual (same each month)"] + MONTH_NAMES, index=0)
    if month_mode == "Annual (same each month)":
        st.session_state.current_month = None
    else:
        st.session_state.current_month = MONTH_NAMES.index(month_mode)

    # Load month data into working entries
    current_month = st.session_state.current_month
    if current_month is not None:
        st.session_state.income_entries = list(st.session_state.monthly_data[current_month].get("income", []))
        st.session_state.expense_entries = list(st.session_state.monthly_data[current_month].get("expenses", []))
    else:
        # Annual mode: entries from first month or empty
        if not st.session_state.income_entries and not st.session_state.expense_entries:
            pass  # keep whatever is in session state

    st.markdown("---")
    if st.button("💾 Save All", use_container_width=True, type="primary"):
        # Save current entries to the right month
        if current_month is not None:
            st.session_state.monthly_data[current_month]["income"] = list(st.session_state.income_entries)
            st.session_state.monthly_data[current_month]["expenses"] = list(st.session_state.expense_entries)
        save_data({
            "inputs": {
                "tax_year": tax_year,
                "sl_interest": sl_interest,
                "county": county,
                "monthly_data": {str(k): v for k, v in st.session_state.monthly_data.items()},
            },
        })
        save_custom_sources(CUSTOM)
        st.success("✅ Saved!")

    # History
    if SAVED:
        st.markdown("---")
        st.markdown("#### 📜 History")
        for date_key in sorted(SAVED.keys(), reverse=True)[:5]:
            entry = SAVED[date_key]
            inp = entry.get("inputs", {})
            if st.button(f"📅 {date_key}", key=f"load_{date_key}"):
                # Restore monthly data
                md = inp.get("monthly_data", {})
                for k, v in md.items():
                    st.session_state.monthly_data[int(k)] = v
                st.rerun()

# ── Income Section ─────────────────────────────────────────────────
st.markdown('<p class="section-title">💰 Income</p>', unsafe_allow_html=True)

income_sources = CUSTOM.get("income_sources", list(DEFAULT_INCOME_SOURCES))

# Running total
income_total = sum(e.get("amount", 0) or 0 for e in st.session_state.income_entries)
income_1099_total = sum(e.get("amount", 0) or 0 for e in st.session_state.income_entries if e.get("employment_type") == "1099")
income_w2_total = sum(e.get("amount", 0) or 0 for e in st.session_state.income_entries if e.get("employment_type") == "W-2")

col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${income_total:,.0f}")
col2.metric("1099 Income", f"${income_1099_total:,.0f}")
col3.metric("W-2 Income", f"${income_w2_total:,.0f}")

# Add income entry
with st.expander("➕ Add Income", expanded=True):
    add_cols = st.columns([1, 2, 2, 1])
    new_type = add_cols[0].selectbox("Type", ["1099", "W-2"], key="new_inc_type", label_visibility="collapsed")
    new_source = add_cols[1].selectbox("Source", income_sources, key="new_inc_source", label_visibility="collapsed")
    new_amount = add_cols[2].number_input("Amount ($)", min_value=0, value=0, step=100, key="new_inc_amount", label_visibility="collapsed")
    add_clicked = add_cols[3].button("➕", key="add_inc_btn")

    if new_source == "Other":
        custom_source = st.text_input("Custom source name", key="custom_inc_source")
        if add_clicked and custom_source.strip():
            if custom_source.strip() not in income_sources:
                CUSTOM["income_sources"] = income_sources + [custom_source.strip()]
                save_custom_sources(CUSTOM)
            st.session_state.income_entries.append({
                "employment_type": new_type,
                "source": custom_source.strip(),
                "amount": new_amount,
            })
            st.rerun()
    elif add_clicked and new_amount > 0:
        st.session_state.income_entries.append({
            "employment_type": new_type,
            "source": new_source,
            "amount": new_amount,
        })
        st.rerun()

# Display income entries
for i, entry in enumerate(st.session_state.income_entries):
    cols = st.columns([1, 2, 2, 1])
    type_color = "#16a34a" if entry["employment_type"] == "1099" else "#2563eb"
    cols[0].markdown(f'<span style="color:{type_color};font-weight:600">{entry["employment_type"]}</span>', unsafe_allow_html=True)
    cols[1].write(entry["source"])
    cols[2].write(f"${entry['amount']:,.0f}")
    if cols[3].button("🗑️", key=f"del_inc_{i}"):
        st.session_state.income_entries.pop(i)
        st.rerun()

# ── Expense Section ────────────────────────────────────────────────
st.markdown('<p class="section-title">📉 Expenses</p>', unsafe_allow_html=True)

expense_categories = CUSTOM.get("expense_categories", list(DEFAULT_EXPENSE_CATEGORIES))

# Running total
expense_total = sum(e.get("amount", 0) or 0 for e in st.session_state.expense_entries)

col1, col2 = st.columns(2)
col1.metric("Total Expenses", f"${expense_total:,.0f}")
col2.metric("Net (Income - Expenses)", f"${income_total - expense_total:,.0f}")

# Add expense entry
with st.expander("➕ Add Expense", expanded=True):
    add_cols = st.columns([2, 2, 2, 1])
    new_cat = add_cols[0].selectbox("Category", expense_categories, key="new_exp_cat", label_visibility="collapsed")
    new_desc = add_cols[1].text_input("Description", key="new_exp_desc", label_visibility="collapsed", placeholder="Description")
    new_exp_amount = add_cols[2].number_input("Amount ($)", min_value=0, value=0, step=10, key="new_exp_amount", label_visibility="collapsed")
    add_exp_clicked = add_cols[3].button("➕", key="add_exp_btn")

    if new_cat == "Other":
        custom_cat = st.text_input("Custom category name", key="custom_exp_cat")
        if add_exp_clicked and custom_cat.strip():
            if custom_cat.strip() not in expense_categories:
                CUSTOM["expense_categories"] = expense_categories + [custom_cat.strip()]
                save_custom_sources(CUSTOM)
            st.session_state.expense_entries.append({
                "category": custom_cat.strip(),
                "amount": new_exp_amount,
                "description": new_desc,
            })
            st.rerun()
    elif add_exp_clicked and new_exp_amount > 0:
        st.session_state.expense_entries.append({
            "category": new_cat,
            "amount": new_exp_amount,
            "description": new_desc,
        })
        st.rerun()

# Display expense entries
for i, entry in enumerate(st.session_state.expense_entries):
    cols = st.columns([2, 2, 2, 1])
    cols[0].write(entry["category"])
    cols[1].write(entry.get("description", ""))
    cols[2].write(f"${entry['amount']:,.0f}")
    if cols[3].button("🗑️", key=f"del_exp_{i}"):
        st.session_state.expense_entries.pop(i)
        st.rerun()

# ── Sync entries to monthly data ──────────────────────────────────
if current_month is not None:
    st.session_state.monthly_data[current_month]["income"] = list(st.session_state.income_entries)
    st.session_state.monthly_data[current_month]["expenses"] = list(st.session_state.expense_entries)
else:
    # Annual mode: apply same entries to all 12 months
    for i in range(12):
        st.session_state.monthly_data[i]["income"] = list(st.session_state.income_entries)
        st.session_state.monthly_data[i]["expenses"] = list(st.session_state.expense_entries)

# ── Calculate ─────────────────────────────────────────────────────
income_entries = st.session_state.income_entries
expense_entries = st.session_state.expense_entries

if not income_entries:
    st.info("👆 Add your income sources above to see your tax calculation.")
    st.stop()

monthly_data = st.session_state.monthly_data
# Check if any monthly data has entries
has_monthly_data = any(
    m.get("income") or m.get("expenses")
    for m in monthly_data.values()
)

if has_monthly_data:
    r = calculate([], [], sl_interest, county, tax_year, monthly_data=monthly_data)
else:
    r = calculate(income_entries, expense_entries, sl_interest, county, tax_year)


def fmt(v): return f"${v:,.0f}" if abs(v) >= 1 else f"${v:,.2f}"


# ── Monthly report cards ───────────────────────────────────────────
st.markdown('<p class="section-title">Monthly Overview</p>', unsafe_allow_html=True)
cols = st.columns(4)
cards = [
    ("Take-Home", fmt(r["monthly_take_home"]), "per month after all taxes"),
    ("Total Tax", fmt(r["monthly_total_tax"]), f"effective rate {r['effective_rate']:.1f}%"),
    ("Avg Monthly Income", fmt(r["avg_monthly_income"]), "gross income"),
    ("Self-Employment Tax", fmt(r["monthly_se_tax"]), "Social Security + Medicare"),
]
for col, (title, value, sub) in zip(cols, cards):
    col.markdown(f"""<div class="card"><h3>{title}</h3><div class="value">{value}</div><div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

# ── Income breakdown ───────────────────────────────────────────────
st.markdown('<p class="section-title">Income Breakdown</p>', unsafe_allow_html=True)
inc_cols = st.columns(3)
inc_cols[0].metric("1099 Income", fmt(r["total_1099_income"]), f"net: {fmt(r['net_1099_income'])}")
inc_cols[1].metric("W-2 Income", fmt(r["total_w2_income"]), "no SE tax")
inc_cols[2].metric("SE Tax", fmt(r["se_tax"]), "15.3% × 92.35%")

# ── Per-month breakdown ────────────────────────────────────────────
if r.get("per_month"):
    has_monthly_variety = any(m.get("income", 0) > 0 for m in r["per_month"])
    if has_monthly_variety:
        st.markdown('<p class="section-title">Monthly Breakdown</p>', unsafe_allow_html=True)
        import pandas as pd
        pm_rows = []
        for m in r["per_month"]:
            if m["income"] > 0 or m["expenses"] > 0:
                pm_rows.append({
                    "Month": m["month"][:3],
                    "1099": m.get("income_1099", 0),
                    "W-2": m.get("income_w2", 0),
                    "Total Income": m["income"],
                    "Expenses": m["expenses"],
                    "Tax": m["tax"],
                    "Take-Home": m["take_home"],
                })
        if pm_rows:
            pm_df = pd.DataFrame(pm_rows)
            st.dataframe(pm_df, use_container_width=True, hide_index=True)

        # Monthly chart
        import plotly.graph_objects as go
        fig_monthly = go.Figure()
        months_short = [m["month"][:3] for m in r["per_month"]]
        fig_monthly.add_trace(go.Bar(x=months_short, y=[m["income"] for m in r["per_month"]], name="Income", marker_color="#0D7377"))
        fig_monthly.add_trace(go.Bar(x=months_short, y=[m["take_home"] for m in r["per_month"]], name="Take-Home", marker_color="#14A3A8"))
        fig_monthly.update_layout(title="Monthly Income vs Take-Home", barmode="group", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_monthly, use_container_width=True)

# ── Step-by-step calculation ──────────────────────────────────────
st.markdown('<p class="section-title">Step-by-Step Calculation (Annual)</p>', unsafe_allow_html=True)

from src.calculator import SL_PHASEOUT_START_SINGLE

steps = [
    ("1099 gross income", fmt(r["total_1099_income"]), "self-employment"),
    ("W-2 income", fmt(r["total_w2_income"]), "employer payroll"),
    ("Total gross income", fmt(r["annual_gross"]), "1099 + W-2"),
    ("Business expenses", fmt(r["annual_expenses"]), "deductible from 1099"),
    ("1099 net income", fmt(r["net_1099_income"]), "1099 − expenses"),
    ("Self-employment tax (15.3% × 92.35%)", fmt(r["se_tax"]), f"on {fmt(r['net_1099_income'] * 0.9235)} taxable base"),
    ("½ SE tax deduction", f"−{fmt(r['se_deduction'])}", "deductible from income"),
    ("Adjusted Gross Income (AGI)", fmt(r["agi"]), "W-2 + 1099 net − ½ SE tax"),
    ("Student loan interest deduction", f"−{fmt(r['sl_deduction'])}", f"phase-out starts at ${SL_PHASEOUT_START_SINGLE:,}" if r['sl_deduction'] < sl_interest else "full deduction"),
    ("Standard deduction", f"−{fmt(r['std_deduction'])}", f"single filer, {tax_year}"),
    ("Taxable income", fmt(r["taxable_income"]), "AGI − deductions"),
    ("Federal income tax", fmt(r["federal_tax"]), "marginal brackets"),
    ("Maryland state tax", fmt(r["md_tax"]), "progressive brackets"),
    (f"{county} local tax ({r['local_rate']*100:.2f}%)", fmt(r["local_tax"]), f"on taxable income"),
    ("Total annual tax", fmt(r["total_tax"]), "SE + federal + state + local"),
    ("Annual take-home pay", fmt(r["annual_take_home"]), "net income − total tax"),
]

step_html = ""
for label, value, note in steps:
    neg = " neg" if value.startswith("−") else ""
    step_html += f'<div class="step-row"><span class="step-label">{label}</span><span><span class="step-value{neg}">{value}</span> <span class="sub">{note}</span></span></div>'

st.markdown(f'<div class="card">{step_html}</div>', unsafe_allow_html=True)

# ── Quarterly payment schedule ─────────────────────────────────────
st.markdown('<p class="section-title">Quarterly Estimated Tax Payments</p>', unsafe_allow_html=True)
q_cols = st.columns(4)
labels = ["Q1", "Q2", "Q3", "Q4"]
for i, (col, label) in enumerate(zip(q_cols, labels)):
    col.markdown(f"""<div class="card"><h3>{label}</h3><div class="value">{fmt(r['quarterly_payment'])}</div><div class="sub">Due {r['q_dates'][i]}</div></div>""", unsafe_allow_html=True)

# ── Tax bracket visualization ──────────────────────────────────────
st.markdown('<p class="section-title">Federal Tax Bracket Breakdown</p>', unsafe_allow_html=True)
import plotly.graph_objects as go

brackets = r["fed_bracket_detail"]
fig = go.Figure()
labels_bar = []
values_bar = []
colors = ["#0D7377", "#14A3A8", "#2DD4BF", "#5EEAD4", "#99F6E4", "#CCFBF1", "#F0FDFA"]
for i, b in enumerate(brackets):
    label = f"{b['rate']*100:.0f}%"
    labels_bar.append(label)
    values_bar.append(b["tax_in_bracket"])

fig.add_trace(go.Bar(x=labels_bar, y=values_bar, marker_color=colors[:len(labels_bar)],
    text=[fmt(v) for v in values_bar], textposition="outside"))
fig.update_layout(title="Federal Tax by Bracket", xaxis_title="Bracket", yaxis_title="Tax ($)",
    height=350, margin=dict(l=0, r=0, t=40, b=0), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# ── Export report ──────────────────────────────────────────────────
st.markdown('<p class="section-title">Export Report</p>', unsafe_allow_html=True)

# Build income source list for report
inc_lines = []
for e in income_entries:
    inc_lines.append(f"  {e['employment_type']} - {e['source']}: {fmt(e['amount'])}/mo")
inc_detail = "\n".join(inc_lines) if inc_lines else "  (none)"

exp_lines = []
for e in expense_entries:
    desc = f" ({e['description']})" if e.get("description") else ""
    exp_lines.append(f"  {e['category']}{desc}: {fmt(e['amount'])}/mo")
exp_detail = "\n".join(exp_lines) if exp_lines else "  (none)"

report_lines = [
    f"1099/W-2 Tax Estimate — {r['tax_year']}",
    f"{'='*50}",
    f"",
    f"INCOME SOURCES (monthly)",
    f"{'-'*50}",
    inc_detail,
    f"",
    f"EXPENSES (monthly)",
    f"{'-'*50}",
    exp_detail,
    f"",
    f"ANNUAL CALCULATION",
    f"{'-'*50}",
    f"1099 gross income:            {fmt(r['total_1099_income'])}",
    f"W-2 income:                    {fmt(r['total_w2_income'])}",
    f"Total gross income:            {fmt(r['annual_gross'])}",
    f"Business expenses:             {fmt(r['annual_expenses'])}",
    f"1099 net income:               {fmt(r['net_1099_income'])}",
    f"Self-employment tax:           {fmt(r['se_tax'])}",
    f"  (½ SE deduction):            {fmt(r['se_deduction'])}",
    f"AGI:                           {fmt(r['agi'])}",
    f"Student loan interest ded:     {fmt(r['sl_deduction'])}",
    f"Standard deduction:            {fmt(r['std_deduction'])}",
    f"Taxable income:                {fmt(r['taxable_income'])}",
    f"Federal income tax:            {fmt(r['federal_tax'])}",
    f"Maryland state tax:            {fmt(r['md_tax'])}",
    f"{county} local tax:             {fmt(r['local_tax'])}",
    f"Total tax:                     {fmt(r['total_tax'])}",
    f"Annual take-home:              {fmt(r['annual_take_home'])}",
    f"Effective tax rate:            {r['effective_rate']:.1f}%",
    f"",
    f"QUARTERLY ESTIMATED PAYMENTS",
    f"{'-'*50}",
    f"Q1 ({r['q_dates'][0]}):  {fmt(r['quarterly_payment'])}",
    f"Q2 ({r['q_dates'][1]}):  {fmt(r['quarterly_payment'])}",
    f"Q3 ({r['q_dates'][2]}):  {fmt(r['quarterly_payment'])}",
    f"Q4 ({r['q_dates'][3]}):  {fmt(r['quarterly_payment'])}",
    f"",
    f"DISCLAIMER: This is an estimate only and does not constitute tax advice.",
]

report_text = "\n".join(report_lines)
st.text_area("Report", report_text, height=300)

st.download_button("📥 Download Report as Text", report_text, file_name=f"tax_estimate_{tax_year}.txt", mime="text/plain")

# ── Disclaimer ─────────────────────────────────────────────────────
st.markdown("""<div class="disclaimer">⚠️ <strong>Disclaimer:</strong> This calculator provides estimates only and is not tax advice. Tax laws change, individual situations vary, and this tool may not account for all deductions, credits, or special rules. Consult a qualified tax professional for your specific situation.</div>""", unsafe_allow_html=True)