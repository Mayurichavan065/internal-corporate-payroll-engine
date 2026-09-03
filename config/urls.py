from django.contrib import admin
from django.urls import path

from payroll.views import (
    apply_leave,
    bulk_onboarding,
    download_payslip,
    employee_dashboard,
    employee_leave_history,
    home,
    manage_bonuses,
    manager_employees,
    manager_login,
    manager_logout,
    monthly_payroll_api,
    payroll_calculation,
    payslip_list,
    pending_leaves,
    update_leave_status,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", manager_login, name="manager_login"),
    path("home/", home, name="home"),
    path("manager/login/", manager_login, name="manager_login"),
    path("manager/logout/", manager_logout, name="manager_logout"),
    path("leave/apply/", apply_leave, name="apply_leave"),
    path("leave/pending/", pending_leaves, name="pending_leaves"),
    path("manager/employees/", manager_employees, name="manager_employees"),
    path("manager/bonuses/", manage_bonuses, name="manage_bonuses"),
    path("hr/onboarding/", bulk_onboarding, name="bulk_onboarding"),
    path(
        "leave/<int:leave_id>/<str:status>/",
        update_leave_status,
        name="update_leave_status",
    ),
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
    path("payslips/", payslip_list, name="payslip_list"),
    path(
        "leave/history/<str:employee_id>/",
        employee_leave_history,
        name="employee_leave_history",
    ),
    path(
        "api/payroll/<str:employee_id>/<int:year>/<int:month>/",
        monthly_payroll_api,
        name="monthly_payroll_api",
    ),
    path("payroll/calculate/", payroll_calculation, name="payroll_calculation"),
    path(
        "payslip/<int:payslip_id>/download/",
        download_payslip,
        name="download_payslip",
    ),
]
