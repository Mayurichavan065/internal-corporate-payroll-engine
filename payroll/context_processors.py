from .models import Employee


def payroll_navigation(request):
    if not request.user.is_authenticated:
        return {"is_payroll_manager": False}
    employee = Employee.objects.filter(
        email=request.user.email,
        is_active=True,
    ).first()
    return {
        "is_payroll_manager": bool(
            employee and employee.team_members.filter(is_active=True).exists()
        )
    }
