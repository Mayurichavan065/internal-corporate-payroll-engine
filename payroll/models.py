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

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type} - {self.status}"