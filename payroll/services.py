from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .models import Employee


TWO_PLACES = Decimal("0.01")

# India new-regime slabs for FY 2026-27, kept here as a versioned policy table.
INDIA_NEW_REGIME_SLABS = (
    (Decimal("400000"), Decimal("0")),
    (Decimal("800000"), Decimal("0.05")),
    (Decimal("1200000"), Decimal("0.10")),
    (Decimal("1600000"), Decimal("0.15")),
    (Decimal("2000000"), Decimal("0.20")),
    (Decimal("2400000"), Decimal("0.25")),
    (None, Decimal("0.30")),
)
INDIA_STANDARD_DEDUCTION = Decimal("75000")
INDIA_REBATE_LIMIT = Decimal("1200000")
INDIA_REBATE_MAX = Decimal("60000")
INDIA_CESS_RATE = Decimal("0.04")


def _money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _progressive_tax(annual_income):
    tax = Decimal("0")
    lower_bound = Decimal("0")

    for upper_bound, rate in INDIA_NEW_REGIME_SLABS:
        taxable = annual_income - lower_bound
        if upper_bound is not None:
            taxable = min(taxable, upper_bound - lower_bound)
        if taxable > 0:
            tax += taxable * rate
        if upper_bound is None or annual_income <= upper_bound:
            break
        lower_bound = upper_bound

    return _money(tax)


def _india_new_regime_tax(annual_gross):
    taxable_income = max(annual_gross - INDIA_STANDARD_DEDUCTION, Decimal("0"))
    tax_before_rebate = _progressive_tax(taxable_income)
    rebate = (
        min(tax_before_rebate, INDIA_REBATE_MAX)
        if taxable_income <= INDIA_REBATE_LIMIT
        else Decimal("0")
    )
    income_tax = max(tax_before_rebate - rebate, Decimal("0"))
    cess = income_tax * INDIA_CESS_RATE
    return _money(income_tax + cess)


def calculate_monthly_payroll(employee, year, month):
    month_start = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    month_end = date(year, month, days_in_month)

    annual_base = employee.base_salary
    if annual_base is None:
        annual_base = employee.salary_band.min_salary

    monthly_base = annual_base / Decimal("12")
    unpaid_days = 0
    for leave in employee.leave_requests.filter(
        leave_type="UNPAID",
        status="APPROVED",
        start_date__lte=month_end,
        end_date__gte=month_start,
    ):
        overlap_start = max(leave.start_date, month_start)
        overlap_end = min(leave.end_date, month_end)
        unpaid_days += (overlap_end - overlap_start).days + 1

    unpaid_deduction = monthly_base * unpaid_days / Decimal(days_in_month)
    bonuses = employee.bonuses.filter(
        bonus_date__gte=month_start,
        bonus_date__lte=month_end,
    )
    bonus_total = sum((bonus.amount for bonus in bonuses), Decimal("0"))
    gross_pay = monthly_base - unpaid_deduction + bonus_total
    annualized_gross = max(gross_pay, Decimal("0")) * Decimal("12")
    tax = _india_new_regime_tax(annualized_gross) / Decimal("12")
    net_pay = gross_pay - tax

    return {
        "employee_id": employee.employee_id,
        "employee_name": employee.full_name,
        "year": year,
        "month": month,
        "currency": "INR",
        "tax_regime": "India new regime",
        "standard_deduction": _money(INDIA_STANDARD_DEDUCTION),
        "annual_base_salary": _money(annual_base),
        "monthly_base_salary": _money(monthly_base),
        "unpaid_leave_days": unpaid_days,
        "unpaid_leave_deduction": _money(unpaid_deduction),
        "bonuses": _money(bonus_total),
        "gross_salary": _money(gross_pay),
        "tax": _money(tax),
        "net_salary": _money(net_pay),
    }