from django.contrib import admin
from django.urls import path

from payroll.views import (
    apply_leave,
    home,
    manager_login,
    manager_logout,
    pending_leaves,
    manager_employees,
    manage_bonuses,
    update_leave_status,
    employee_dashboard,
    payslip_list,
    employee_leave_history,
    monthly_payroll_api,
    payroll_calculation,
    download_payslip,
)

urlpatterns = [

    # Admin
    path(
        "admin/",
        admin.site.urls
    ),

    # Login page # if someone openns the home url then it call the manager_login function in views.py   
    path(
        "",
        manager_login,
        name="manager_login"
    ),
    path(
        "home/",
        home,
        name="home",
    ),

    path(
        "manager/login/",
        manager_login,
        name="manager_login"
    ),

    # Logout
    path(
        "manager/logout/",
        manager_logout,
        name="manager_logout"
    ),

    # Employee applies leave
    path(
        "leave/apply/",
        apply_leave,
        name="apply_leave"
    ),

    # Manager pending leaves
    path(
        "leave/pending/",
        pending_leaves,
        name="pending_leaves"
    ),
    path("manager/employees/", manager_employees, name="manager_employees"),
    path("manager/bonuses/", manage_bonuses, name="manage_bonuses"),

    # Approve / Reject
    path(
        "leave/<int:leave_id>/<str:status>/",
        update_leave_status,
        name="update_leave_status"
    ),

    # Employee dashboard
    path(
        "employee/dashboard/",
        employee_dashboard,
        name="employee_dashboard"
    ),
    path("payslips/", payslip_list, name="payslip_list"),

    # Employee leave history
    path(
        "leave/history/<str:employee_id>/",
        employee_leave_history,
        name="employee_leave_history"
    ),

    path(
        "api/payroll/<str:employee_id>/<int:year>/<int:month>/",
        monthly_payroll_api,
        name="monthly_payroll_api"
    ),

    path(
        "payroll/calculate/",
        payroll_calculation,
        name="payroll_calculation"
    ),
    path(
        "payslip/<int:payslip_id>/download/",
        download_payslip,
        name="download_payslip",
    ),
]