from django.contrib import admin
from django.urls import path

from payroll.views import (
    apply_leave,
    manager_login,
    manager_logout,
    pending_leaves,
    update_leave_status,
    employee_dashboard,
    employee_leave_history
)

urlpatterns = [

    # Admin
    path(
        "admin/",
        admin.site.urls
    ),

    # Login page
    path(
        "",
        manager_login,
        name="manager_login"
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

    # Employee leave history
    path(
        "leave/history/<str:employee_id>/",
        employee_leave_history,
        name="employee_leave_history"
    ),
]