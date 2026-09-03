from django.db import models
from django.core.exceptions import ValidationError


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

    def clean(self):
        if self.min_salary is not None and self.max_salary is not None:
            if self.min_salary > self.max_salary:
                raise ValidationError(
                    "Minimum salary cannot be greater than maximum salary."
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

    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual base salary. Defaults to the salary band minimum when blank."
    )

    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members"
    )

    joining_date = models.DateField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"


class LeaveRequest(models.Model):

    LEAVE_TYPE_CHOICES = [
        ("CASUAL", "Casual Leave"),
        ("SICK", "Sick Leave"),
        ("PAID", "Paid Leave"),
        ("UNPAID", "Unpaid Leave"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests"
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_TYPE_CHOICES
    )

    start_date = models.DateField()

    end_date = models.DateField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError(
                    "Leave end date cannot be before the start date."
                )

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type} - {self.status}"


class Bonus(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="bonuses"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bonus_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["bonus_date", "id"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.amount} - {self.bonus_date}"