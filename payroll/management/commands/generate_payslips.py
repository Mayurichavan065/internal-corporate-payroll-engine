from calendar import month_name
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from payroll.models import Employee, Payslip
from payroll.services import calculate_monthly_payroll


class Command(BaseCommand):
    help = "Generate private PDF payslips for all active employees on the 25th."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int)
        parser.add_argument("--month", type=int)
        parser.add_argument("--force", action="store_true", help="Run outside the 25th.")
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        year = options["year"] or run_date.year
        month = options["month"] or run_date.month
        batch_size = options["batch_size"]

        if run_date.day != 25 and not options["force"]:
            self.stdout.write(f"Skipped: scheduled payroll runs on the 25th (today is {run_date}).")
            return
        if not 1 <= month <= 12:
            raise CommandError("month must be between 1 and 12")
        if year < 1:
            raise CommandError("year must be positive")
        if batch_size < 1:
            raise CommandError("batch-size must be positive")

        employee_ids = Employee.objects.filter(is_active=True).values_list("pk", flat=True)
        generated = 0
        for start in range(0, employee_ids.count(), batch_size):
            ids = employee_ids[start:start + batch_size]
            employees = Employee.objects.filter(pk__in=ids).select_related("salary_band")
            for employee in employees:
                self._generate_for_employee(employee, year, month)
                generated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Generated {generated} payslip(s) for {month_name[month]} {year}."
        ))

    @staticmethod
    def _generate_for_employee(employee, year, month):
        payroll = calculate_monthly_payroll(employee, year, month)
        pdf = BytesIO()
        document = canvas.Canvas(pdf, pagesize=letter)
        document.setTitle(f"Payslip {employee.employee_id} {year}-{month:02d}")
        document.setFont("Helvetica-Bold", 18)
        document.drawString(72, 730, "Corporate Payroll Payslip")
        document.setFont("Helvetica", 11)
        lines = (
            ("Employee", f"{employee.full_name} ({employee.employee_id})"),
            ("Period", f"{month_name[month]} {year}"),
            ("Annual base salary", payroll["annual_base_salary"]),
            ("Monthly base salary", payroll["monthly_base_salary"]),
            ("Unpaid leave days", payroll["unpaid_leave_days"]),
            ("Unpaid leave deduction", payroll["unpaid_leave_deduction"]),
            ("Bonuses", payroll["bonuses"]),
            ("Gross salary", payroll["gross_salary"]),
            ("Tax", payroll["tax"]),
            ("Net salary", payroll["net_salary"]),
        )
        y = 680
        for label, value in lines:
            document.drawString(72, y, f"{label}: {value}")
            y -= 28
        document.showPage()
        document.save()
        pdf.seek(0)

        with transaction.atomic():
            payslip, _ = Payslip.objects.get_or_create(
                employee=employee,
                period_year=year,
                period_month=month,
            )
            if payslip.pdf:
                payslip.pdf.delete(save=False)
            payslip.pdf.save(
                f"{employee.employee_id}-{year}-{month:02d}.pdf",
                ContentFile(pdf.read()),
                save=True,
            )
