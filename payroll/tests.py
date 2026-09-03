from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Department, SalaryBand, Employee, LeaveRequest, Bonus
from .services import calculate_monthly_payroll


class EmployeeHierarchyTest(TestCase):
    """Tests the employee-manager hierarchy for V1."""

    def setUp(self):
        # Create the IT department
        self.department = Department.objects.create(
            name="IT",
            description="Information Technology"
        )

        # Create salary bands used by our test employees
        self.senior_band = SalaryBand.objects.create(
            name="Senior",
            min_salary=90000,
            max_salary=150000
        )

        self.mid_level_band = SalaryBand.objects.create(
            name="Mid-Level",
            min_salary=50000,
            max_salary=90000
        )

        self.junior_band = SalaryBand.objects.create(
            name="Junior",
            min_salary=25000,
            max_salary=50000
        )

        self.intern_band = SalaryBand.objects.create(
            name="Intern",
            min_salary=10000,
            max_salary=20000
        )

        # Mayuri is the top-level manager
        self.manager = Employee.objects.create(
            employee_id="EMP101",
            full_name="Mayuri Chavan",
            email="mayuri.chavan@test.com",
            department=self.department,
            salary_band=self.senior_band,
            joining_date=date.today()
        )

        # Raj reports to Mayuri
        self.employee1 = Employee.objects.create(
            employee_id="EMP102",
            full_name="Raj Patil",
            email="raj.patil@test.com",
            department=self.department,
            salary_band=self.mid_level_band,
            manager=self.manager,
            joining_date=date.today()
        )

        # Mayur reports to Mayuri
        self.employee2 = Employee.objects.create(
            employee_id="EMP103",
            full_name="Mayur Kolekar",
            email="mayur.kolekar@test.com",
            department=self.department,
            salary_band=self.junior_band,
            manager=self.manager,
            joining_date=date.today()
        )

        # Mittal reports to Mayuri
        self.employee3 = Employee.objects.create(
            employee_id="EMP104",
            full_name="Mittal Shisode",
            email="mittal.shisode@test.com",
            department=self.department,
            salary_band=self.intern_band,
            manager=self.manager,
            joining_date=date.today()
        )

    def test_employee_has_manager(self):
        # Check that Raj's manager is Mayuri
        self.assertEqual(
            self.employee1.manager,
            self.manager
        )

    def test_manager_has_team_members(self):
        # Get all employees reporting to Mayuri
        team_members = self.manager.team_members.all()

        # Check that all three team members are present
        self.assertIn(self.employee1, team_members)
        self.assertIn(self.employee2, team_members)
        self.assertIn(self.employee3, team_members)

    def test_manager_has_three_team_members(self):
        # Check that Mayuri has exactly three direct reports
        self.assertEqual(
            self.manager.team_members.count(),
            3
        )


class LeaveWorkflowTest(EmployeeHierarchyTest):
    """Tests the authenticated leave workflow for V2."""

    def setUp(self):
        super().setUp()
        self.manager_user = User.objects.create_user(
            username="mayuri",
            password="password123",
            email=self.manager.email
        )
        self.employee_user = User.objects.create_user(
            username="raj",
            password="password123",
            email=self.employee1.email
        )
        self.other_manager_user = User.objects.create_user(
            username="mayur",
            password="password123",
            email=self.employee2.email
        )

    def test_employee_creates_pending_leave_for_self(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("apply_leave"),
            {
                "leave_type": "CASUAL",
                "start_date": "2026-09-01",
                "end_date": "2026-09-02",
                "reason": "Personal appointment",
                "employee": self.employee3.id,
            }
        )

        self.assertRedirects(response, reverse("apply_leave"))
        leave = LeaveRequest.objects.get()
        self.assertEqual(leave.employee, self.employee1)
        self.assertEqual(leave.status, "PENDING")

    def test_designated_manager_can_approve_team_leave(self):
        leave = LeaveRequest.objects.create(
            employee=self.employee1,
            leave_type="SICK",
            start_date="2026-09-01",
            end_date="2026-09-01",
            reason="Illness"
        )
        self.client.force_login(self.manager_user)

        response = self.client.post(
            reverse("update_leave_status", args=[leave.id, "APPROVED"])
        )

        self.assertRedirects(response, reverse("pending_leaves"))
        leave.refresh_from_db()
        self.assertEqual(leave.status, "APPROVED")

    def test_non_manager_cannot_change_leave_status(self):
        leave = LeaveRequest.objects.create(
            employee=self.employee1,
            leave_type="PAID",
            start_date="2026-09-03",
            end_date="2026-09-03",
            reason="Vacation"
        )
        self.client.force_login(self.other_manager_user)

        response = self.client.post(
            reverse("update_leave_status", args=[leave.id, "REJECTED"])
        )

        self.assertEqual(response.status_code, 404)
        leave.refresh_from_db()
        self.assertEqual(leave.status, "PENDING")

    def test_leave_end_date_cannot_be_before_start_date(self):
        leave = LeaveRequest(
            employee=self.employee1,
            leave_type="CASUAL",
            start_date="2026-09-05",
            end_date="2026-09-01",
            reason="Invalid dates"
        )

        with self.assertRaises(ValidationError):
            leave.full_clean()

    def test_employee_cannot_view_another_employee_history(self):
        self.client.force_login(self.employee_user)

        response = self.client.get(
            reverse("employee_leave_history", args=[self.employee2.employee_id])
        )

        self.assertEqual(response.status_code, 403)


class PayrollCalculationTest(EmployeeHierarchyTest):
    """Tests monthly payroll calculations for V3."""

    def setUp(self):
        super().setUp()
        self.employee1.base_salary = 120000
        self.employee1.save(update_fields=["base_salary"])

    def test_calculation_deducts_approved_unpaid_leave_and_adds_bonus(self):
        LeaveRequest.objects.create(
            employee=self.employee1,
            leave_type="UNPAID",
            start_date="2026-09-01",
            end_date="2026-09-02",
            reason="Personal leave",
            status="APPROVED",
        )
        LeaveRequest.objects.create(
            employee=self.employee1,
            leave_type="UNPAID",
            start_date="2026-09-03",
            end_date="2026-09-04",
            reason="Pending leave",
            status="PENDING",
        )
        Bonus.objects.create(
            employee=self.employee1,
            amount=1000,
            bonus_date="2026-09-15",
            description="Performance bonus",
        )

        payroll = calculate_monthly_payroll(self.employee1, 2026, 9)

        self.assertEqual(payroll["unpaid_leave_days"], 2)
        self.assertEqual(payroll["bonuses"], Decimal("1000.00"))
        self.assertEqual(payroll["gross_salary"], Decimal("10333.33"))
        self.assertEqual(payroll["tax"], Decimal("1900.21"))
        self.assertEqual(payroll["net_salary"], Decimal("8433.12"))

    def test_employee_can_fetch_own_monthly_payroll(self):
        employee_user = User.objects.create_user(
            username="raj-payroll",
            password="password123",
            email=self.employee1.email,
        )
        self.client.force_login(employee_user)

        response = self.client.get(
            reverse(
                "monthly_payroll_api",
                args=[self.employee1.employee_id, 2026, 9],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["employee_id"], self.employee1.employee_id)