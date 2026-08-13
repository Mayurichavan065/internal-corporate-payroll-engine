from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class SalaryBand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    min_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    max_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.name


class Employee(models.Model):
    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    full_name = models.CharField(max_length=150)

    email = models.EmailField(unique=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    salary_band = models.ForeignKey(
        SalaryBand,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    manager = models.ForeignKey(
        "self",  # The Manager is also an Employee
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members"
    )

    joining_date = models.DateField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"