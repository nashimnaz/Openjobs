from django.db import migrations


def create_default_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    roles = [
        ("CANDIDATE", "Candidate seeking employment opportunities."),
        ("EMPLOYER", "Employer hiring talent and managing organization job postings."),
        ("ADMINISTRATOR", "Platform administrator with system-wide management privileges."),
    ]
    for name, desc in roles:
        Role.objects.get_or_create(name=name, defaults={"description": desc})


def remove_default_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name__in=["CANDIDATE", "EMPLOYER", "ADMINISTRATOR"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_roles, remove_default_roles),
    ]
