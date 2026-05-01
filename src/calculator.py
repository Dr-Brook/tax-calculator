"""Tax calculation logic for 1099/self-employment + W-2 mixed income."""

from .counties import COUNTY_RATES


# ── 2024 Single brackets ──────────────────────────────────────────
FED_BRACKETS_2024 = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float("inf"), 0.37),
]

STD_DEDUCTION_2024 = 14600

MD_BRACKETS_2024 = [
    (1000, 0.02),
    (2000, 0.03),
    (3000, 0.04),
    (100000, 0.0475),
    (125000, 0.05),
    (150000, 0.0525),
    (250000, 0.055),
    (float("inf"), 0.0575),
]

# ── 2025 Single brackets ──────────────────────────────────────────
FED_BRACKETS_2025 = [
    (11925, 0.10),
    (48475, 0.12),
    (103350, 0.22),
    (197300, 0.24),
    (250525, 0.32),
    (626350, 0.35),
    (float("inf"), 0.37),
]

STD_DEDUCTION_2025 = 15000

MD_BRACKETS_2025 = [
    (1000, 0.02),
    (2000, 0.03),
    (3000, 0.04),
    (100000, 0.0475),
    (125000, 0.05),
    (150000, 0.0525),
    (250000, 0.055),
    (float("inf"), 0.0575),
]

# ── 2026 Single brackets (OBBBA + IRS Rev Proc 2025-32) ────────────
FED_BRACKETS_2026 = [
    (12400, 0.10),
    (50400, 0.12),
    (105700, 0.22),
    (201775, 0.24),
    (256225, 0.32),
    (640600, 0.35),
    (float("inf"), 0.37),
]

STD_DEDUCTION_2026 = 16100

MD_BRACKETS_2026 = [
    (1000, 0.02),
    (2000, 0.03),
    (3000, 0.04),
    (100000, 0.0475),
    (125000, 0.05),
    (150000, 0.0525),
    (250000, 0.055),
    (float("inf"), 0.0575),
]

SE_TAX_RATE = 0.153
SE_WAGE_BASE = 0.9235  # 92.35% of net SE income subject to SE tax
SL_INTEREST_MAX = 2500
SL_PHASEOUT_START_SINGLE = 80000
SL_PHASEOUT_END_SINGLE = 95000
IRS_MILEAGE_RATES = {2024: 0.67, 2025: 0.70, 2026: 0.725}  # dollars per mile


def _apply_brackets(income, brackets):
    """Calculate tax using marginal brackets."""
    tax = 0.0
    prev = 0
    for ceiling, rate in brackets:
        if income <= prev:
            break
        taxable = min(income, ceiling) - prev
        tax += taxable * rate
        prev = ceiling
    return tax


MONTH_NAMES = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]


def _aggregate_entries(income_entries, expense_entries):
    """Aggregate income/expense entry lists into totals by type.
    
    Returns: (total_1099_income, total_w2_income, total_1099_expenses, total_all_expenses)
    
    Business expenses are deducted from 1099 income only (TCJA rules).
    """
    total_1099 = 0.0
    total_w2 = 0.0
    total_1099_expenses = 0.0  # expenses deductible against 1099 income
    total_all_expenses = 0.0
    total_mileage_deduction = 0.0

    for entry in (income_entries or []):
        amt = entry.get("amount", 0) or 0
        if entry.get("employment_type") == "1099":
            total_1099 += amt
            # Mileage deduction for 1099 rideshare/driving income
            mileage_ded = entry.get("mileage_deduction", 0) or 0
            total_mileage_deduction += mileage_ded
            total_1099_expenses += mileage_ded
            total_all_expenses += mileage_ded
        else:
            total_w2 += amt

    for entry in (expense_entries or []):
        amt = entry.get("amount", 0) or 0
        total_all_expenses += amt
        # All business expenses are deductible from 1099 income
        # (under TCJA, W-2 employees can't deduct unreimbursed business expenses)
        total_1099_expenses += amt

    return total_1099, total_w2, total_1099_expenses, total_all_expenses, total_mileage_deduction


def calculate(income_entries, expense_entries, sl_interest_annual, county, tax_year=2025, monthly_data=None):
    """Full tax calculation returning a dict with all results.
    
    income_entries: list of dicts with keys: employment_type ("W-2" or "1099"), source (str), amount (float)
    expense_entries: list of dicts with keys: category (str), amount (float), description (str)
    sl_interest_annual: student loan interest paid per year
    county: Maryland county name
    tax_year: 2024 or 2025
    monthly_data: optional dict of {month_index: {"income": [...entries], "expenses": [...entries]}}
    
    If monthly_data is provided, entries are summed across all months for annual totals.
    If income_entries/expense_entries are provided directly, they represent annual totals.
    """

    if tax_year == 2026:
        brackets_fed = FED_BRACKETS_2026
        std_deduction = STD_DEDUCTION_2026
        brackets_md = MD_BRACKETS_2026
    elif tax_year == 2025:
        brackets_fed = FED_BRACKETS_2025
        std_deduction = STD_DEDUCTION_2025
        brackets_md = MD_BRACKETS_2025
    else:
        brackets_fed = FED_BRACKETS_2024
        std_deduction = STD_DEDUCTION_2024
        brackets_md = MD_BRACKETS_2024
    local_rate = COUNTY_RATES.get(county, 0.032)

    # ── Aggregate from monthly_data or from direct entries ───────
    per_month = None

    if monthly_data:
        # Sum across all months
        total_1099 = 0.0
        total_w2 = 0.0
        total_1099_expenses = 0.0
        total_all_expenses = 0.0
        total_mileage_deduction = 0.0
        per_month = []

        for i in range(12):
            m_data = monthly_data.get(i, {"income": [], "expenses": []})
            m_inc = m_data.get("income", [])
            m_exp = m_data.get("expenses", [])
            m_1099, m_w2, m_exp1099, m_exp_all, m_mileage = _aggregate_entries(m_inc, m_exp)
            total_1099 += m_1099
            total_w2 += m_w2
            total_1099_expenses += m_exp1099
            total_all_expenses += m_exp_all
            total_mileage_deduction += m_mileage

            m_gross = m_1099 + m_w2
            per_month.append({
                "month": MONTH_NAMES[i],
                "month_index": i,
                "income_1099": m_1099,
                "income_w2": m_w2,
                "income": m_gross,
                "expenses": m_exp_all,
                "expenses_1099_ded": m_exp1099,
                "mileage_deduction": m_mileage,
            })

        # For per-month tax calc, we'll compute annual first then pro-rate
        annual_gross = total_1099 + total_w2
        annual_expenses = total_all_expenses
    else:
        total_1099, total_w2, total_1099_expenses, total_all_expenses, total_mileage_deduction = _aggregate_entries(
            income_entries, expense_entries
        )
        annual_gross = total_1099 + total_w2
        annual_expenses = total_all_expenses

    # ── 1099 net income (after business expenses including mileage) ─
    net_1099 = max(0, total_1099 - total_1099_expenses)

    # ── Mileage deduction summary (for display) ──────────────────
    mileage_deduction_total = total_mileage_deduction

    # ── Self-employment tax (only on 1099 income) ─────────────────
    se_taxable = net_1099 * SE_WAGE_BASE
    se_tax = se_taxable * SE_TAX_RATE
    se_deduction = se_tax / 2  # deductible half

    # ── Adjusted Gross Income ─────────────────────────────────────
    # W-2 income is full amount, 1099 net minus half SE tax
    agi = total_w2 + net_1099 - se_deduction

    # ── Student loan interest deduction (phase-out) ───────────────
    sl_deduction = min(sl_interest_annual, SL_INTEREST_MAX)
    if agi > SL_PHASEOUT_START_SINGLE:
        phase_out = min((agi - SL_PHASEOUT_START_SINGLE) / (SL_PHASEOUT_END_SINGLE - SL_PHASEOUT_START_SINGLE), 1.0)
        sl_deduction = max(sl_deduction * (1 - phase_out), 0)

    # ── Taxable income (federal) ──────────────────────────────────
    taxable_income = max(0, agi - sl_deduction - std_deduction)

    # ── Federal income tax ────────────────────────────────────────
    federal_tax = _apply_brackets(taxable_income, brackets_fed)

    # ── Maryland state tax ────────────────────────────────────────
    md_tax = _apply_brackets(taxable_income, brackets_md)

    # ── Local county tax ──────────────────────────────────────────
    local_tax = taxable_income * local_rate

    # ── Totals ────────────────────────────────────────────────────
    total_tax = se_tax + federal_tax + md_tax + local_tax
    annual_net = annual_gross - annual_expenses
    annual_take_home = annual_net - total_tax
    effective_rate = (total_tax / annual_net * 100) if annual_net > 0 else 0

    # ── Quarterly payments ─────────────────────────────────────────
    quarterly = total_tax / 4

    if tax_year == 2026:
        q_dates = ["Apr 15, 2026", "Jun 15, 2026", "Sep 15, 2026", "Jan 15, 2027"]
    elif tax_year == 2025:
        q_dates = ["Apr 15, 2025", "Jun 15, 2025", "Sep 15, 2025", "Jan 15, 2026"]
    else:
        q_dates = ["Apr 15, 2024", "Jun 15, 2024", "Sep 15, 2024", "Jan 15, 2025"]

    # ── Monthly averages ──────────────────────────────────────────
    monthly_take_home = annual_take_home / 12
    avg_monthly_income = annual_gross / 12

    # ── Per-month tax allocation ──────────────────────────────────
    if per_month:
        # Calculate the effective marginal rate once
        marginal_rate = total_tax / annual_gross if annual_gross > 0 else 0
        for m in per_month:
            m_gross = m["income"]
            m_exp = m["expenses"]
            m_net = m_gross - m_exp
            # Pro-rate each tax component by income share
            share = m_gross / annual_gross if annual_gross > 0 else 1 / 12
            m_se_tax = se_tax * share
            m_federal_tax = federal_tax * share
            m_md_tax = md_tax * share
            m_local_tax = local_tax * share
            m_tax = m_se_tax + m_federal_tax + m_md_tax + m_local_tax
            m_take_home = m_net - m_tax
            m["net"] = m_net
            m["tax"] = m_tax
            m["se_tax"] = m_se_tax
            m["federal_tax"] = m_federal_tax
            m["md_tax"] = m_md_tax
            m["local_tax"] = m_local_tax
            m["take_home"] = m_take_home
            m["effective_rate"] = (m_tax / m_net * 100) if m_net > 0 else 0
            m["set_aside"] = m_tax  # how much to put aside this month

    # ── Federal bracket breakdown for visualization ──────────────
    fed_bracket_detail = []
    prev = 0
    for ceiling, rate in brackets_fed:
        if taxable_income <= prev:
            break
        bracket_taxable = min(taxable_income, ceiling) - prev
        bracket_tax = bracket_taxable * rate
        fed_bracket_detail.append({
            "range_start": prev,
            "range_end": ceiling,
            "rate": rate,
            "taxable_in_bracket": bracket_taxable,
            "tax_in_bracket": bracket_tax,
        })
        prev = ceiling

    return {
        # Monthly averages
        "monthly_income": avg_monthly_income,
        "monthly_expenses": annual_expenses / 12,
        "monthly_net": annual_net / 12,
        "monthly_se_tax": se_tax / 12,
        "monthly_federal_tax": federal_tax / 12,
        "monthly_md_tax": md_tax / 12,
        "monthly_local_tax": local_tax / 12,
        "monthly_total_tax": total_tax / 12,
        "monthly_take_home": monthly_take_home,
        # Annual
        "annual_gross": annual_gross,
        "annual_expenses": annual_expenses,
        "annual_net": annual_net,
        # Breakdown
        "total_1099_income": total_1099,
        "total_w2_income": total_w2,
        "net_1099_income": net_1099,
        "total_1099_expenses": total_1099_expenses,
        "mileage_deduction_total": mileage_deduction_total,
        # Tax components
        "se_tax": se_tax,
        "se_deduction": se_deduction,
        "agi": agi,
        "sl_deduction": sl_deduction,
        "std_deduction": std_deduction,
        "taxable_income": taxable_income,
        "federal_tax": federal_tax,
        "md_tax": md_tax,
        "local_tax": local_tax,
        "total_tax": total_tax,
        "annual_take_home": annual_take_home,
        "effective_rate": effective_rate,
        # Quarterly
        "quarterly_payment": quarterly,
        "q_dates": q_dates,
        # Visualization
        "fed_bracket_detail": fed_bracket_detail,
        # Per-month data
        "per_month": per_month,
        "avg_monthly_income": avg_monthly_income,
        # Meta
        "county": county,
        "local_rate": local_rate,
        "tax_year": tax_year,
    }