from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .models import Employee


TWO_PLACES = Decimal("0.01")

# Annual progressive brackets for a single taxpayer.
TAX_BRACKETS = (
    (Decimal("11600"), Decimal("0.10")),
    (Decimal("47150"), Decimal("0.12")),
    (Decimal("100525"), Decimal("0.22")),
    (Decimal("191950"), Decimal("0.24")),
    (Decimal("243725"), Decimal("0.32")),
    (Decimal("609350"), Decimal("0.35")),
    (None, Decimal("0.37")),
)


def _money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _progressive_tax(annual_income):
    tax = Decimal("0")
    lower_bound = Decimal("0")

    for upper_bound, rate in TAX_BRACKETS:
        taxable = annual_income - lower_bound
        if upper_bound is not None:
            taxable = min(taxable, upper_bound - lower_bound)
        if taxable > 0:
            tax += taxable * rate
        if upper_bound is None or annual_income <= upper_bound:
            break
        lower_bound = upper_bound

    return _money(tax)


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
    tax = _progressive_tax(max(gross_pay, Decimal("0")) * Decimal("12")) / Decimal("12")
    net_pay = gross_pay - tax

    return {
        "employee_id": employee.employee_id,
        "employee_name": employee.full_name,
        "year": year,
        "month": month,
        "annual_base_salary": _money(annual_base),
        "monthly_base_salary": _money(monthly_base),
        "unpaid_leave_days": unpaid_days,
        "unpaid_leave_deduction": _money(unpaid_deduction),
        "bonuses": _money(bonus_total),
        "gross_salary": _money(gross_pay),
        "tax": _money(tax),
        "net_salary": _money(net_pay),
    }