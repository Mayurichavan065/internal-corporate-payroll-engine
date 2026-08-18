from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import Employee, LeaveRequest


# --------------------------------------------------
# Home / Welcome Page
# --------------------------------------------------

def home(request):
    return render(request, "home.html")


# --------------------------------------------------
# V2 - Employee applies for leave
# --------------------------------------------------

def apply_leave(request):

    employees = Employee.objects.filter(is_active=True)

    if request.method == "POST":

        employee_id = request.POST.get("employee")
        leave_type = request.POST.get("leave_type")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        employee = Employee.objects.get(id=employee_id)

        LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )

        return redirect("apply_leave")

    return render(
        request,
        "leave_apply.html",
        {
            "employees": employees
        }
    )


# --------------------------------------------------
# Login - Employee + Manager
# --------------------------------------------------

def manager_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            return render(
                request,
                "login.html",
                {
                    "error": "Invalid username or password."
                }
            )

        employee = Employee.objects.filter(
            email=user.email
        ).first()

        if not employee:
            return render(
                request,
                "login.html",
                {
                    "error": "No employee record is linked to this account."
                }
            )

        login(request, user)

        # Employee with team members = Manager
        if employee.team_members.exists():
            return redirect("pending_leaves")

        # Normal employee
        return redirect("employee_dashboard")

    return render(
        request,
        "login.html"
    )


# --------------------------------------------------
# V2 - Manager sees pending leaves
# --------------------------------------------------

@login_required(login_url="manager_login")
def pending_leaves(request):

    try:

        manager = Employee.objects.get(
            email=request.user.email
        )

    except Employee.DoesNotExist:

        return render(
            request,
            "pending_leaves.html",
            {
                "leaves": [],
                "error": "No employee record is linked to this account."
            }
        )

    team_members = Employee.objects.filter(
        manager=manager,
        is_active=True
    )

    leaves = LeaveRequest.objects.filter(
        employee__in=team_members,
        status="PENDING"
    ).select_related(
        "employee",
        "employee__manager"
    )

    return render(
        request,
        "pending_leaves.html",
        {
            "leaves": leaves,
            "manager": manager
        }
    )


# --------------------------------------------------
# V2 - Manager approves/rejects leave
# --------------------------------------------------

@login_required(login_url="manager_login")
def update_leave_status(request, leave_id, status):

    leave = get_object_or_404(
        LeaveRequest,
        id=leave_id
    )

    if status in ["APPROVED", "REJECTED"]:

        leave.status = status

        leave.save(
            update_fields=["status"]
        )

    return redirect("pending_leaves")


# --------------------------------------------------
# V2 - Manager Logout
# --------------------------------------------------

@login_required(login_url="manager_login")
def manager_logout(request):

    logout(request)

    return redirect("manager_login")


# --------------------------------------------------
# Employee Dashboard
# --------------------------------------------------

@login_required(login_url="manager_login")
def employee_dashboard(request):

    employee = Employee.objects.filter(
        email=request.user.email
    ).first()

    if not employee:

        logout(request)

        return redirect("manager_login")

    leaves = LeaveRequest.objects.filter(
        employee=employee
    ).order_by("-created_at")

    return render(
        request,
        "employee_dashboard.html",
        {
            "employee": employee,
            "leaves": leaves
        }
    )


# --------------------------------------------------
# Employee Leave History
# --------------------------------------------------

@login_required(login_url="manager_login")
def employee_leave_history(request, employee_id):

    employee = get_object_or_404(
        Employee,
        employee_id=employee_id
    )

    leaves = LeaveRequest.objects.filter(
        employee=employee
    ).order_by("-created_at")

    return render(
        request,
        "employee_leave_history.html",
        {
            "employee": employee,
            "leaves": leaves
        }
    )