from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET

from .models import Bonus, Employee, LeaveRequest, Payslip
from .services import OnboardingError, bulk_onboard_from_csv, calculate_monthly_payroll

def home(request):
    return render(request, "home.html")


@login_required(login_url="manager_login")
def apply_leave(request):

    employee = Employee.objects.filter(
        email=request.user.email,
        is_active=True
    ).first()

    if not employee:
        logout(request)
        return redirect("manager_login")
    if request.method == "POST":

        leave_type = request.POST.get("leave_type")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        leave = LeaveRequest(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )

        try:
            leave.full_clean()
        except ValidationError as error:
            return render(
                request,
                "leave_apply.html",
                {
                    "employee": employee,
                    "error": error.messages[0]
                },
                status=400
            )

        leave.save()

        return redirect("apply_leave")

    return render(
        request,
        "leave_apply.html",
        {
            "employee": employee
        }
    )


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
        employee = Employee.objects.filter(email=user.email).first()

        if not employee and user.is_staff:
            login(request, user)
            return redirect("bulk_onboarding")

        if not employee or not employee.is_active:
            return render(
                request,
                "login.html",
                {
                    "error": "No employee record is linked to this account."
                }
            )

        login(request, user)

        if employee.team_members.filter(is_active=True).exists():
            return redirect("pending_leaves")
        return redirect("employee_dashboard")

    return render(
        request,
        "login.html"
    )


# --------------------------------------------------
# V2 - Manager sees pending leaves
# --------------------------------------------------

# If the user is not logged in, Django sends them to the login page.
@login_required(login_url="manager_login")
def pending_leaves(request):

    try:
# The view finds the logged-in employee:
        manager = Employee.objects.get(
            email=request.user.email
        )

    except Employee.DoesNotExist:

        return render(
            request,
            "pending_leaves.html",# redirect to html for aprrove or reject req
            {
                "leaves": [],
                "error": "No employee record is linked to this account."
            }
        )
    if not manager.is_active or not manager.team_members.filter(is_active=True).exists():
        return HttpResponseForbidden("Only managers can view pending leave requests.")
# Then it finds that manager’s active team members
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


@login_required(login_url="manager_login")
def manager_employees(request):
    manager = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    if not manager or not manager.team_members.filter(is_active=True).exists():
        return HttpResponseForbidden("Only managers can view team employees.")
    employees = manager.team_members.filter(is_active=True).select_related(
        "department", "salary_band"
    )
    return render(request, "manager_employees.html", {
        "manager": manager,
        "employees": employees,
    })


@login_required(login_url="manager_login")
def manage_bonuses(request):
    manager = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    if not manager or not manager.team_members.filter(is_active=True).exists():
        return HttpResponseForbidden("Only managers can manage team bonuses.")
    employees = manager.team_members.filter(is_active=True)
    error = None
    if request.method == "POST":
        employee = employees.filter(employee_id=request.POST.get("employee_id")).first()
        try:
            amount = Decimal(request.POST.get("amount", ""))
            bonus_date = date.fromisoformat(request.POST.get("bonus_date", ""))
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, TypeError, ValueError):
            error = "Enter a valid positive amount and bonus date."
        if not error and not employee:
            error = "Select an employee from your team."
        elif not error:
            employee.bonuses.create(
                amount=amount,
                bonus_date=bonus_date,
                description=request.POST.get("description", "").strip(),
            )
            return redirect("manage_bonuses")
    bonuses = Bonus.objects.filter(employee__in=employees).select_related(
        "employee"
    ).order_by("-bonus_date", "-id")
    return render(request, "manage_bonuses.html", {
        "manager": manager,
        "employees": employees,
        "bonuses": bonuses,
        "error": error,
    })


@login_required(login_url="manager_login")
def bulk_onboarding(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Only HR staff can onboard employees.")
    results = None
    error = None
    if request.method == "POST":
        uploaded_file = request.FILES.get("employee_csv")
        if not uploaded_file:
            error = "Choose a CSV file to upload."
        else:
            try:
                results = bulk_onboard_from_csv(uploaded_file)
            except OnboardingError as onboarding_error:
                error = str(onboarding_error)
    return render(request, "bulk_onboarding.html", {
        "results": results,
        "error": error,
    })


# --------------------------------------------------
# V2 - Manager approves/rejects leave
# --------------------------------------------------

@login_required(login_url="manager_login")
@require_POST
def update_leave_status(request, leave_id, status):

    if status not in ["APPROVED", "REJECTED"]:
        return JsonResponse({"error": "Invalid leave status."}, status=400)

    manager = Employee.objects.filter(email=request.user.email).first()

    if not manager:
        return HttpResponseForbidden("No employee record is linked to this account.")

    leave = get_object_or_404(
        LeaveRequest,
        id=leave_id,
        employee__manager=manager,
        status="PENDING"
    )
# Then it checks the requested status:


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
    payslips = Payslip.objects.filter(
        employee=employee
    ).order_by("-period_year", "-period_month")

    return render(
        request,
        "employee_dashboard.html",
        {
            "employee": employee,
            "leaves": leaves,
            "payslips": payslips,
        }
    )


@login_required(login_url="manager_login")
def payslip_list(request):
    viewer = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    if not viewer:
        logout(request)
        return redirect("manager_login")
    is_manager = viewer.team_members.filter(is_active=True).exists()
    employees = viewer.team_members.filter(is_active=True) if is_manager else Employee.objects.filter(pk=viewer.pk)
    payslips = Payslip.objects.filter(
        employee__in=employees
    ).select_related("employee").order_by(
        "-period_year", "-period_month", "employee__employee_id"
    )
    return render(request, "payslips.html", {
        "viewer": viewer,
        "payslips": payslips,
        "is_manager": is_manager,
    })


# --------------------------------------------------
# Employee Leave History
# --------------------------------------------------

@login_required(login_url="manager_login")
def employee_leave_history(request, employee_id):

    viewer = Employee.objects.filter(
        email=request.user.email,
        is_active=True
    ).first()

    if not viewer:
        logout(request)
        return redirect("manager_login")

    if not (
        viewer.employee_id == employee_id
        or Employee.objects.filter(
            employee_id=employee_id,
            manager=viewer
        ).exists()
    ):
        return HttpResponseForbidden("You cannot view this leave history.")

    employee = get_object_or_404(
        Employee,
        employee_id=employee_id
    )

    leaves = LeaveRequest.objects.filter(
        employee=employee
    ).order_by("-created_at")# shows new req at first

    return render(
        request,
        "employee_leave_history.html",
        {
            "employee": employee,
            "leaves": leaves
        }
    )


@login_required(login_url="manager_login")
@require_GET
def monthly_payroll_api(request, employee_id, year, month):
    if year < 1:
        return JsonResponse({"error": "year must be positive"}, status=400)
    if month < 1 or month > 12:
        return JsonResponse({"error": "month must be between 1 and 12"}, status=400)

    viewer = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    employee = Employee.objects.filter(employee_id=employee_id).first()
    if not viewer or not employee:
        return JsonResponse({"error": "Employee not found"}, status=404)
    if viewer != employee and employee.manager_id != viewer.id:
        return JsonResponse({"error": "You cannot view this payroll"}, status=403)

    return JsonResponse(calculate_monthly_payroll(employee, year, month))


@login_required(login_url="manager_login")
def payroll_calculation(request):
    viewer = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    if not viewer:
        logout(request)
        return redirect("manager_login")

    is_manager = viewer.team_members.filter(is_active=True).exists()
    employees = viewer.team_members.filter(is_active=True) if is_manager else Employee.objects.filter(id=viewer.id)
    selected_employee_id = request.GET.get("employee_id", viewer.employee_id)
    employee = employees.filter(employee_id=selected_employee_id).first()
    try:
        year = int(request.GET.get("year", date.today().year))
        month = int(request.GET.get("month", date.today().month))
    except (TypeError, ValueError):
        year = date.today().year
        month = date.today().month
        error = "Enter a valid year and month."
    else:
        error = None
    result = None

    if error is not None:
        pass
    elif not 1 <= month <= 12 or year < 1:
        error = "Enter a valid year and month."
    elif employee:
        result = calculate_monthly_payroll(employee, year, month)
    else:
        error = "Select an employee you are allowed to view."

    return render(request, "payroll_calculation.html", {
        "employees": employees,
        "employee": employee,
        "is_manager": is_manager,
        "year": year,
        "month": month,
        "result": result,
        "error": error,
    })


@login_required(login_url="manager_login")
def download_payslip(request, payslip_id):
    viewer = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    payslip = get_object_or_404(
        Payslip.objects.select_related("employee"),
        id=payslip_id,
    )
    if not viewer or (
        viewer != payslip.employee
        and payslip.employee.manager_id != viewer.id
    ):
        return HttpResponseForbidden("You cannot download this payslip.")

    response = FileResponse(
        payslip.pdf.open("rb"),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{payslip.employee.employee_id}-'
        f'{payslip.period_year}-{payslip.period_month:02d}.pdf"'
    )
    return response