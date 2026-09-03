from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0004_payslip_payslip_unique_employee_payslip_period"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employee",
            name="base_salary",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Annual base salary in INR. Defaults to the salary band minimum when blank.",
                max_digits=12,
                null=True,
            ),
        ),
    ]
