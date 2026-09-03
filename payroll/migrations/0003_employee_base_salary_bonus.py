from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0002_leaverequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="base_salary",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Annual base salary. Defaults to the salary band minimum when blank.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="Bonus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("bonus_date", models.DateField()),
                ("description", models.CharField(blank=True, max_length=255)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonuses",
                        to="payroll.employee",
                    ),
                ),
            ],
            options={"ordering": ["bonus_date", "id"]},
        ),
    ]