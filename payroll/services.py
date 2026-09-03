from calendar import monthrange
import csv
import re
import secrets
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import TextIOWrapper

from django.contrib.auth.models import User
from django.db import transaction

from .models import Department, Employee, SalaryBand


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
    if taxable_income > INDIA_REBATE_LIMIT:
        marginal_relief_limit = taxable_income - INDIA_REBATE_LIMIT
        income_tax = min(income_tax, marginal_relief_limit)
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
    leave_ranges = []
    for leave in employee.leave_requests.filter(
        leave_type="UNPAID",
        status="APPROVED",
        start_date__lte=month_end,
        end_date__gte=month_start,
    ):
        overlap_start = max(leave.start_date, month_start)
        overlap_end = min(leave.end_date, month_end)
        leave_ranges.append((overlap_start, overlap_end))

    unpaid_days = 0
    current_start = None
    current_end = None
    for overlap_start, overlap_end in sorted(leave_ranges):
        if current_start is not None and overlap_start <= current_end:
            current_end = max(current_end, overlap_end)
            continue
        if current_start is not None:
            unpaid_days += (current_end - current_start).days + 1
        current_start, current_end = overlap_start, overlap_end
    if current_start is not None:
        unpaid_days += (current_end - current_start).days + 1

    unpaid_deduction = monthly_base * unpaid_days / Decimal(days_in_month)
    bonuses = employee.bonuses.filter(
        bonus_date__gte=month_start,
        bonus_date__lte=month_end,
    )
    bonus_total = sum((bonus.amount for bonus in bonuses), Decimal("0"))
    gross_pay = monthly_base - unpaid_deduction + bonus_total
    annualized_gross = max(
        monthly_base * Decimal("12")
        - unpaid_deduction * Decimal("12")
        + bonus_total,
        Decimal("0"),
    )
    annual_tax = _india_new_regime_tax(annualized_gross)
    tax = annual_tax / Decimal("12")
    net_pay = gross_pay - tax

    return {
        "employee_id": employee.employee_id,
        "employee_name": employee.full_name,
        "year": year,
        "month": month,
        "currency": "INR",
        "tax_regime": "India new regime",
        "standard_deduction": _money(INDIA_STANDARD_DEDUCTION),
        "annual_tax": _money(annual_tax),
        "annual_base_salary": _money(annual_base),
        "monthly_base_salary": _money(monthly_base),
        "unpaid_leave_days": unpaid_days,
        "unpaid_leave_deduction": _money(unpaid_deduction),
        "bonuses": _money(bonus_total),
        "gross_salary": _money(gross_pay),
        "tax": _money(tax),
        "net_salary": _money(net_pay),
    }


class OnboardingError(ValueError):
    pass


def bulk_onboard_from_csv(uploaded_file):
    """Validate and create at most 50 employee accounts as one transaction."""
    try:
        uploaded_file.seek(0)
        rows = list(
            csv.DictReader(
                TextIOWrapper(uploaded_file, encoding="utf-8-sig", newline="")
            )
        )
    except (UnicodeDecodeError, csv.Error) as error:
        raise OnboardingError("Upload a valid UTF-8 CSV file.") from error

    required = {"full_name", "email", "department", "salary_band"}
    headers = set(rows[0].keys()) if rows else set()
    missing = required - headers
    if missing:
        raise OnboardingError(f"Missing CSV columns: {', '.join(sorted(missing))}.")
    if not rows:
        raise OnboardingError("The CSV file does not contain any hires.")
    if len(rows) > 50:
        raise OnboardingError("Upload no more than 50 hires at a time.")

    prepared = []
    seen_emails = set()
    for row_number, row in enumerate(rows, start=2):
        full_name = row["full_name"].strip()
        email = row["email"].strip().lower()
        department_name = row["department"].strip()
        salary_band_name = row["salary_band"].strip()
        if not full_name or not email or not department_name or not salary_band_name:
            raise OnboardingError(
                f"Row {row_number}: name, email, department, and salary band are required."
            )
        if email in seen_emails or User.objects.filter(email__iexact=email).exists():
            raise OnboardingError(f"Row {row_number}: email {email} is already in use.")
        seen_emails.add(email)
        try:
            department = Department.objects.get(name__iexact=department_name)
            salary_band = SalaryBand.objects.get(name__iexact=salary_band_name)
        except (Department.DoesNotExist, SalaryBand.DoesNotExist) as error:
            raise OnboardingError(f"Row {row_number}: department or salary band was not found.") from error
        base_salary = None
        if row.get("base_salary", "").strip():
            try:
                base_salary = Decimal(row["base_salary"].strip())
            except Exception as error:
                raise OnboardingError(f"Row {row_number}: base_salary must be a valid INR amount.") from error
            if base_salary <= 0:
                raise OnboardingError(f"Row {row_number}: base_salary must be positive.")
        joining_date = date.today()
        if row.get("joining_date", "").strip():
            try:
                joining_date = date.fromisoformat(row["joining_date"].strip())
            except ValueError as error:
                raise OnboardingError(f"Row {row_number}: joining_date must use YYYY-MM-DD.") from error
        manager = None
        manager_id = row.get("manager_employee_id", "").strip()
        if manager_id:
            manager = Employee.objects.filter(employee_id=manager_id, is_active=True).first()
            if not manager:
                raise OnboardingError(f"Row {row_number}: manager employee ID was not found.")
        prepared.append(
            {
                "full_name": full_name,
                "email": email,
                "department": department,
                "salary_band": salary_band,
                "base_salary": base_salary,
                "joining_date": joining_date,
                "manager": manager,
            }
        )

    with transaction.atomic():
        existing_ids = set(Employee.objects.values_list("employee_id", flat=True))
        next_number = max(
            [int(match.group(1)) for value in existing_ids if (match := re.fullmatch(r"EMP(\d+)", value))],
            default=100,
        ) + 1
        results = []
        for data in prepared:
            while f"EMP{next_number}" in existing_ids:
                next_number += 1
            employee_id = f"EMP{next_number}"
            password = secrets.token_urlsafe(9)
            user = User.objects.create_user(
                username=employee_id.lower(),
                email=data["email"],
                password=password,
            )
            employee = Employee.objects.create(employee_id=employee_id, **data)
            results.append({"employee": employee, "username": user.username, "password": password})
            existing_ids.add(employee_id)
            next_number += 1
    return results