import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from src.calculator import calculate
from src.counties import COUNTY_RATES

# ── Data persistence ─────────────────────────────────────────────
SAVE_FILE = Path(__file__).parent / "data" / "saved_data.json"

def load_saved_data():
    """Load previously saved input data."""
    if SAVE_FILE.exists():
        try:
            return json.loads(SAVE_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {}

def save_data(data: dict):
    """Save input data and calculation results locally."""
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = load_saved_data()
    # Store by date key so we keep history
    date_key = datetime.now().strftime("%Y-%m-%d")
    existing[date_key] = {
        "inputs": data["inputs"],
        "results": data["results"],
        "saved_at": datetime.now().isoformat(),
    }
    # Keep last 50 entries
    if len(existing) > 50:
        keys = sorted(existing.keys())
        for k in keys[:-50]:
            del existing[k]
    SAVE_FILE.write_text(json.dumps(existing, indent=2))

SAVED = load_saved_data()

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
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────
st.markdown("""<div class="header-bar"><h1>🧮 1099 / Self-Employment Tax Calculator</h1>
<p>Estimate your federal, state & local taxes — including quarterly payments</p></div>""", unsafe_allow_html=True)

# ── Sidebar inputs ─────────────────────────────────────────────────
with st.sidebar:
    st.header("📊 Your Info")

    # Load last saved values as defaults
    last_saved = SAVED.get(sorted(SAVED.keys())[-1], {}) if SAVED else {}
    last_inputs = last_saved.get("inputs", {}) if last_saved else {}

    tax_year = st.selectbox("Tax Year", [2025, 2024], index=[2025, 2024].index(last_inputs.get("tax_year", 2025)))
    
    income_mode = st.radio("Income Entry", ["Same each month", "Per month"], index=0, horizontal=True)
    
    if income_mode == "Same each month":
        monthly_income = st.number_input("Monthly gross income ($)", min_value=0, value=last_inputs.get("monthly_income", 8000), step=500)
        monthly_incomes = None
    else:
        st.caption("Enter your 1099 income for each month:")
        monthly_incomes = {}
        default_income = last_inputs.get("monthly_income", 8000)
        saved_months = last_inputs.get("monthly_incomes", {})
        month_cols = st.columns(3)
        month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        for i, month in enumerate(month_names):
            col = month_cols[i % 3]
            default_val = saved_months.get(str(i), default_income)
            val = col.number_input(f"{month[:3]}", min_value=0, value=default_val, step=500, key=f"month_{i}")
            monthly_incomes[i] = val
        monthly_income = sum(monthly_incomes.values()) / 12  # average for fallback
    
    monthly_expenses = st.number_input("Monthly business expenses ($)", min_value=0, value=last_inputs.get("monthly_expenses", 200), step=100)
    sl_interest = st.number_input("Student loan interest paid/year ($)", min_value=0, max_value=10000, value=last_inputs.get("sl_interest", 2500), step=100)
    county = st.selectbox("Maryland County", list(COUNTY_RATES.keys()), index=list(COUNTY_RATES.keys()).index(last_inputs.get("county", "Montgomery")))
    st.caption(f"Local tax rate: {COUNTY_RATES[county]*100:.2f}%")

    # Save button
    if st.button("💾 Save Calculation", use_container_width=True, type="primary"):
        inputs_to_save = {
            "tax_year": tax_year,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "sl_interest": sl_interest,
            "county": county,
            "income_mode": income_mode,
        }
        if monthly_incomes:
            inputs_to_save["monthly_incomes"] = {str(k): v for k, v in monthly_incomes.items()}
        save_data({
            "inputs": inputs_to_save,
            "results": r if 'r' in dir() else {},
        })
        st.success("✅ Saved! Your data will be here next time you open the app.")

    # History
    if SAVED:
        st.markdown("---")
        st.markdown("#### 📜 History")
        for date_key in sorted(SAVED.keys(), reverse=True)[:5]:
            entry = SAVED[date_key]
            inp = entry.get("inputs", {})
            if st.button(f"{date_key} — ${inp.get('monthly_income', 0):,}/mo", key=f"load_{date_key}"):
                st.session_state["loaded_date"] = date_key
                st.rerun()

# ── Calculate ─────────────────────────────────────────────────────
if monthly_incomes:
    r = calculate(monthly_income, monthly_expenses, sl_interest, county, tax_year, monthly_incomes=monthly_incomes)
else:
    r = calculate(monthly_income, monthly_expenses, sl_interest, county, tax_year)

def fmt(v): return f"${v:,.0f}" if abs(v) >= 1 else f"${v:,.2f}"

# ── Monthly report cards ───────────────────────────────────────────
st.markdown('<p class="section-title">Monthly Overview</p>', unsafe_allow_html=True)
cols = st.columns(4)
if monthly_incomes:
    avg_income = r["avg_monthly_income"]
else:
    avg_income = r["monthly_income"]
cards = [
    ("Take-Home", fmt(r["monthly_take_home"]), "per month after all taxes"),
    ("Total Tax", fmt(r["monthly_total_tax"]), f"effective rate {r['effective_rate']:.1f}%"),
    ("Avg Monthly Income", fmt(avg_income), "gross income" if not monthly_incomes else "average across months"),
    ("Self-Employment Tax", fmt(r["monthly_se_tax"]), "Social Security + Medicare"),
]
for col, (title, value, sub) in zip(cols, cards):
    col.markdown(f"""<div class="card"><h3>{title}</h3><div class="value">{value}</div><div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

# ── Per-month breakdown ────────────────────────────────────────────
if r.get("per_month"):
    st.markdown('<p class="section-title">Monthly Income Breakdown</p>', unsafe_allow_html=True)
    import pandas as pd
    pm_df = pd.DataFrame(r["per_month"])
    st.dataframe(
        pm_df[["month", "income", "expenses", "net", "tax", "take_home"]].rename(columns={
            "month": "Month", "income": "Income", "expenses": "Expenses",
            "net": "Net", "tax": "Tax", "take_home": "Take-Home"
        }),
        use_container_width=True,
        column_config={
            "Income": st.column_config.NumberColumn(format="$%,d"),
            "Expenses": st.column_config.NumberColumn(format="$%,d"),
            "Net": st.column_config.NumberColumn(format="$%,d"),
            "Tax": st.column_config.NumberColumn(format="$%,d"),
            "Take-Home": st.column_config.NumberColumn(format="$%,d"),
        },
        hide_index=True,
    )
    # Monthly income chart
    import plotly.graph_objects as go
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(x=[m["month"][:3] for m in r["per_month"]], y=[m["income"] for m in r["per_month"]], name="Income", marker_color="#0D7377"))
    fig_monthly.add_trace(go.Bar(x=[m["month"][:3] for m in r["per_month"]], y=[m["take_home"] for m in r["per_month"]], name="Take-Home", marker_color="#14A3A8"))
    fig_monthly.update_layout(title="Monthly Income vs Take-Home", barmode="group", height=350, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_monthly, use_container_width=True)

# ── Step-by-step calculation ──────────────────────────────────────
st.markdown('<p class="section-title">Step-by-Step Calculation (Annual)</p>', unsafe_allow_html=True)

steps = [
    ("Gross income", fmt(r["annual_gross"]), f"({fmt(r['avg_monthly_income'])} avg/mo × 12)" if monthly_incomes else f"({fmt(r['monthly_income'])} × 12)"),
    ("Business expenses", fmt(r["annual_expenses"]), f"({fmt(r['monthly_expenses'])} × 12)"),
    ("Net income", fmt(r["annual_net"]), "gross − expenses"),
    ("Self-employment tax (15.3% × 92.35%)", fmt(r["se_tax"]), f"on {fmt(r['annual_net'] * 0.9235)} taxable base"),
    ("½ SE tax deduction", f"−{fmt(r['se_deduction'])}", "deductible from income"),
    ("Adjusted Gross Income (AGI)", fmt(r["agi"]), "net income − ½ SE tax"),
    ("Student loan interest deduction", f"−{fmt(r['sl_deduction'])}", f"phase-out starts at ${SL_PHASEOUT_START_SINGLE:,}" if r['sl_deduction'] < sl_interest else "full deduction"),
    ("Standard deduction", f"−{fmt(r['std_deduction'])}", f"single filer, {tax_year}"),
    ("Taxable income", fmt(r["taxable_income"]), "AGI − deductions"),
    ("Federal income tax", fmt(r["federal_tax"]), "marginal brackets"),
    ("Maryland state tax", fmt(r["md_tax"]), "progressive brackets"),
    (f"{county} local tax ({r['local_rate']*100:.2f}%)", fmt(r["local_tax"]), f"on taxable income"),
    ("Total annual tax", fmt(r["total_tax"]), "SE + federal + state + local"),
    ("Annual take-home pay", fmt(r["annual_take_home"]), "net income − total tax"),
]

# Import constant for display
from src.calculator import SL_PHASEOUT_START_SINGLE

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

report_lines = [
    f"1099/Self-Employment Tax Estimate — {r['tax_year']}",
    f"{'='*50}",
    f"Monthly gross income:        {fmt(r['monthly_income'])}",
    f"Monthly business expenses:    {fmt(r['monthly_expenses'])}",
    f"Monthly net income:           {fmt(r['monthly_net'])}",
    f"",
    f"ANNUAL CALCULATION",
    f"{'-'*50}",
    f"Gross income:                 {fmt(r['annual_gross'])}",
    f"Business expenses:             {fmt(r['annual_expenses'])}",
    f"Net income:                    {fmt(r['annual_net'])}",
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

import json
st.download_button("📥 Download Report as Text", report_text, file_name=f"tax_estimate_{tax_year}.txt", mime="text/plain")

# ── Disclaimer ─────────────────────────────────────────────────────
st.markdown("""<div class="disclaimer">⚠️ <strong>Disclaimer:</strong> This calculator provides estimates only and is not tax advice. Tax laws change, individual situations vary, and this tool may not account for all deductions, credits, or special rules. Consult a qualified tax professional for your specific situation.</div>""", unsafe_allow_html=True)