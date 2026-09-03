# Internal Corporate Payroll Engine

This is a Django web application for internal leave and employee management workflows.
The project includes:

- Employee, department, and salary-band data models
- Manager and employee login-based dashboards
- Leave application and approval/rejection flow
- Admin panel for data management
- Monthly INR payroll calculation API with unpaid-leave deductions, bonuses, and India new-regime tax

## Project Structure

```
internal-corporate-payroll-engine/
|-- manage.py
|-- requirements.txt
|-- config/
|   |-- settings.py
|   `-- urls.py
|-- payroll/
|   |-- models.py
|   |-- services.py
|   |-- views.py
|   |-- tests.py
|   |-- management/commands/generate_payslips.py
|   `-- templates/
`-- templates/                 # project-level error templates
```

## How URL Routing Works

All routes are configured in `config/urls.py`.

Each `path(...)` does three things:

1. Matches a URL pattern from the browser request.
2. Calls a Python view function from `payroll/views.py`.
3. Optionally passes named URL parameters to that view.

### URL Map

| URL Pattern                                | View Function            | Route Name               | Purpose                            |
|--------------------------------------------|--------------------------|--------------------------|------------------------------------|
| `admin/`                                   | `admin.site.urls`        | `-`                      | Django admin panel                 |
| `/`                                        | `manager_login`          | `manager_login`          | Default entry page (login)         |
| `manager/login/`                           | `manager_login`          | `manager_login`          | Explicit login URL                 |
| `manager/logout/`                          | `manager_logout`         | `manager_logout`         | Logout current user                |
| `leave/apply/`                             | `apply_leave`            | `apply_leave`            | Employee leave application form    |
| `leave/pending/`                           | `pending_leaves`         | `pending_leaves`         | Manager pending leave approvals    |
| `leave/<int:leave_id>/<str:status>/`       | `update_leave_status`    | `update_leave_status`    | Approve/reject a leave request     |
| `employee/dashboard/`                      | `employee_dashboard`     | `employee_dashboard`     | Employee personal dashboard        |
| `payslips/`                                | `payslip_list`            | `payslip_list`            | Private payslip document list       |
| `leave/history/<str:employee_id>/`         | `employee_leave_history` | `employee_leave_history` | Employee leave history by employee |
| `manager/employees/`                        | `manager_employees`      | `manager_employees`      | Manager team directory              |
| `manager/bonuses/`                          | `manage_bonuses`         | `manage_bonuses`         | Manager bonus register              |
| `hr/onboarding/`                            | `bulk_onboarding`        | `bulk_onboarding`        | HR bulk CSV onboarding              |

Notes:

- The root URL (`/`) and `/manager/login/` both use the same login view.
- Dynamic route example: `leave/<int:leave_id>/<str:status>/` passes `leave_id` and `status` into the view function.

## How Views Work (Request -> Logic -> Response)

All business logic is in `payroll/views.py`.

### 1) `manager_login(request)`

- GET:
	- Renders `login.html`.
- POST:
	- Reads `username` and `password` from form data.
	- Authenticates using Django `authenticate(...)`.
	- Finds corresponding `Employee` by matching `Employee.email == user.email`.
	- Logs in user via Django `login(...)`.
	- Role split:
		- If employee has team members, redirect to manager screen (`pending_leaves`).
		- Otherwise redirect to employee screen (`employee_dashboard`).

Why this works:

- Manager is inferred from hierarchy (`employee.team_members.exists()`), not a separate role field.

### 2) `apply_leave(request)`

- GET:
	- Loads active employees.
	- Renders `leave_apply.html` with employee dropdown.
- POST:
	- Reads form fields: employee, leave type, start/end dates, reason.
	- Creates `LeaveRequest` with default status `PENDING`.
	- Redirects back to the same form route (`apply_leave`).

### 3) `pending_leaves(request)`

- Protected by `@login_required(login_url="manager_login")`.
- Gets logged-in manager by email.
- Loads active team members where `manager=<current manager>`.
- Fetches only pending leave requests for those team members.
- Renders `pending_leaves.html`.

### 4) `update_leave_status(request, leave_id, status)`

- Protected by `@login_required(...)`.
- Fetches the target leave by `leave_id`.
- Accepts only two status values: `APPROVED` or `REJECTED`.
- Updates and saves status.
- Redirects to pending list.

### 5) `employee_dashboard(request)`

- Protected by `@login_required(...)`.
- Gets logged-in employee by email.
- If no employee record exists, user is logged out and redirected to login.
- Fetches that employee's leaves ordered newest first.
- Renders `employee_dashboard.html`.

### 6) `employee_leave_history(request, employee_id)`

- Protected by `@login_required(...)`.
- Finds employee by business ID (`employee_id`, not DB primary key).
- Fetches leaves ordered newest first.
- Renders `employee_leave_history.html`.

### 7) `manager_logout(request)`

- Protected by `@login_required(...)`.
- Calls Django `logout(...)` and redirects to login.

### 8) `home(request)`

- Returns `home.html`.
- Currently not wired in `config/urls.py`, so it is not reachable by URL unless a route is added.

## Request Flow Examples

### Login Flow

1. Browser requests `/`.
2. URL resolver matches `manager_login`.
3. GET returns login page.
4. User submits credentials (POST).
5. View authenticates and identifies employee.
6. Redirect:
	 - Manager -> `/leave/pending/`
	 - Employee -> `/employee/dashboard/`

### Manager Approval Flow

1. Manager opens `/leave/pending/`.
2. View loads pending requests for manager's team.
3. Template shows Approve/Reject action links.
4. Clicking action calls `/leave/<leave_id>/APPROVED/` or `/leave/<leave_id>/REJECTED/`.
5. Status updates in DB and user is redirected to pending list.

### Employee Leave Application Flow

1. Employee opens `/leave/apply/`.
2. View renders form and employee list.
3. Submit POST creates a `LeaveRequest`.
4. Redirect reloads form page.

## Models Used by Views

The main model relationships that power URL/view behavior are:

- `Employee.manager` -> self reference to another `Employee`
- `Employee.team_members` -> reverse relation for manager hierarchy
- `LeaveRequest.employee` -> leave ownership
- `LeaveRequest.status` -> state machine (`PENDING`, `APPROVED`, `REJECTED`)

These relations are what make manager filtering and leave ownership work.

## Template Mapping

| View Function            | Template File                |
|--------------------------|------------------------------|
| `manager_login`          | `login.html`                 |
| `apply_leave`            | `leave_apply.html`           |
| `pending_leaves`         | `pending_leaves.html`        |
| `employee_dashboard`     | `employee_dashboard.html`    |
| `employee_leave_history` | `employee_leave_history.html`|
| `home`                   | `home.html`                  |

## Authentication and Access Control

- Views requiring authentication are protected with `@login_required`.
- If unauthenticated, Django redirects to route named `manager_login`.
- Session login/logout uses Django auth functions:
	- `login(request, user)`
	- `logout(request)`

## Quick Start

1. Clone repository.
2. Create and activate virtual environment.
3. Install dependencies.
4. Run migrations.
5. Start server.

Example commands:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Run the quality checks before starting the server:

```bash
python manage.py check
python manage.py test
```

Open:

- `http://127.0.0.1:8000/` for login
- `http://127.0.0.1:8000/admin/` for admin panel

## V3 Payroll API

Authenticated employees can request their own monthly payroll, and managers can
request payroll for their direct reports:

```text
GET /api/payroll/<employee_id>/<year>/<month>/
```

The response includes annual and monthly base salary, approved unpaid leave
days, the leave deduction, bonuses recorded in the month, gross salary, tax,
and net salary. `Employee.base_salary` is annual pay in INR; when it is blank,
the salary band minimum is used. Tax uses India's FY 2026-27 new-regime slabs,
a INR 75,000 standard deduction, Section 87A rebate, and 4% health and
education cess. Unpaid leave is deducted from monthly base salary by calendar
day.

## V4 Bulk Payslip Generation

V4 adds a repeatable background management command that generates one private
PDF payslip for every active employee for the selected month. Schedule this
command on the 25th with the host scheduler:

```text
python manage.py generate_payslips
```

The command processes employees in batches of 100, reuses the V3 payroll
service, and stores PDFs under `private_media/payslips/`. That directory is not
served as a public URL. Employees can download only their own payslips, while
managers can download payslips for their direct reports.

For a manual backfill or local test, use explicit values and `--force`:

```text
python manage.py generate_payslips --year 2026 --month 9 --force
```

The command is idempotent for each employee and payroll period, so rerunning
the same task replaces the existing PDF instead of creating a duplicate
record. On Windows, configure Task Scheduler to run the command on the 25th
of each month from the project directory.

## V5 Bulk Onboarding

HR staff can open `/hr/onboarding/` and upload a UTF-8 CSV containing up to 50
new hires. Required columns are `full_name`, `email`, `department`, and
`salary_band`. Optional columns are `base_salary`, `manager_employee_id`, and
`joining_date` in `YYYY-MM-DD` format. Salary values are annual INR.

The import validates every row before creating anything. Each accepted hire
receives the next available `EMP<number>` employee ID, a Django login username,
and a generated temporary password. Passwords are stored only as hashes; the
generated value is displayed once in the HR result screen for secure delivery.
Invalid rows, duplicate emails, unknown departments, unknown salary bands, and
unknown managers reject the complete batch so partial onboarding cannot occur.

## Current Notes

- `/home/` is the public product entry page; `/` remains the sign-in page.
- All application templates use the shared responsive layout in `base.html`.
