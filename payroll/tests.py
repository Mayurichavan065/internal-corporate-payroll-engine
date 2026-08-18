from datetime import date

from django.test import TestCase

from .models import Department, SalaryBand, Employee


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