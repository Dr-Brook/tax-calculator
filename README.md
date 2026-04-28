# 1099/Self-Employment Tax Calculator

A Streamlit app for 1099/self-employed workers in Maryland to estimate monthly and annual tax obligations, including:

- **Self-employment tax** (15.3% on 92.35% of net income)
- **Federal income tax** (2024/2025 brackets, single filer)
- **Maryland state tax** (progressive brackets)
- **Maryland local county tax** (all 24 counties)
- **Student loan interest deduction** (up to $2,500 with phase-out)
- **Quarterly estimated payment schedule**

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

- Step-by-step calculation breakdown
- All 24 Maryland county local tax rates
- Annual + monthly views
- Quarterly payment schedule with due dates
- Tax bracket visualization (Plotly)
- Export report as text

## Disclaimer

This tool provides estimates only and is not tax advice. Consult a qualified tax professional for your specific situation.