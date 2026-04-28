"""Tax calculation logic for 1099/self-employment income."""

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

SE_TAX_RATE = 0.153
SE_WAGE_BASE = 0.9235  # 92.35% of net income subject to SE tax
SL_INTEREST_MAX = 2500
SL_PHASEOUT_START_SINGLE = 80000
SL_PHASEOUT_END_SINGLE = 95000


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


def calculate(monthly_income, monthly_expenses, sl_interest_annual, county, tax_year=2025):
    """Full tax calculation returning a dict with all results."""

    brackets_fed = FED_BRACKETS_2025 if tax_year == 2025 else FED_BRACKETS_2024
    std_deduction = STD_DEDUCTION_2025 if tax_year == 2025 else STD_DEDUCTION_2024
    brackets_md = MD_BRACKETS_2025 if tax_year == 2025 else MD_BRACKETS_2024
    local_rate = COUNTY_RATES.get(county, 0.032)

    # ── Annual figures ────────────────────────────────────────────
    annual_gross = monthly_income * 12
    annual_expenses = monthly_expenses * 12
    annual_net = annual_gross - annual_expenses

    # Self-employment tax
    se_taxable = annual_net * SE_WAGE_BASE
    se_tax = se_taxable * SE_TAX_RATE
    se_deduction = se_tax / 2  # deductible half

    # Adjusted Gross Income
    agi = annual_net - se_deduction

    # Student loan interest deduction (phase-out)
    sl_deduction = min(sl_interest_annual, SL_INTEREST_MAX)
    if agi > SL_PHASEOUT_START_SINGLE:
        phase_out = min((agi - SL_PHASEOUT_START_SINGLE) / (SL_PHASEOUT_END_SINGLE - SL_PHASEOUT_START_SINGLE), 1.0)
        sl_deduction = max(sl_deduction * (1 - phase_out), 0)

    # Taxable income (federal)
    taxable_income = max(0, agi - sl_deduction - std_deduction)

    # Federal income tax
    federal_tax = _apply_brackets(taxable_income, brackets_fed)

    # Maryland state tax
    md_tax = _apply_brackets(taxable_income, brackets_md)

    # Local county tax
    local_tax = taxable_income * local_rate

    # Totals
    total_tax = se_tax + federal_tax + md_tax + local_tax
    annual_take_home = annual_net - total_tax
    effective_rate = (total_tax / annual_net * 100) if annual_net > 0 else 0

    # Quarterly payments
    quarterly = total_tax / 4

    if tax_year == 2025:
        q_dates = ["Apr 15, 2025", "Jun 15, 2025", "Sep 15, 2025", "Jan 15, 2026"]
    else:
        q_dates = ["Apr 15, 2024", "Jun 15, 2024", "Sep 15, 2024", "Jan 15, 2025"]

    # Monthly breakdown
    monthly_take_home = annual_take_home / 12

    # Federal bracket breakdown for visualization
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
        # Monthly
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
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
        # Meta
        "county": county,
        "local_rate": local_rate,
        "tax_year": tax_year,
    }