from django.contrib import admin
from .models import Department, SalaryBand, Employee, LeaveRequest


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(SalaryBand)
class SalaryBandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "min_salary",
        "max_salary",
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "full_name",
        "email",
        "department",
        "salary_band",
        "manager",
        "joining_date",
        "is_active",
    )

    list_filter = (
        "department",
        "salary_band",
        "is_active",
    )

    search_fields = (
        "employee_id",
        "full_name",
        "email",
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "status",
        "created_at",
    )

    list_filter = (
        "leave_type",
        "status",
    )

    search_fields = (
        "employee__employee_id",
        "employee__full_name",
    )