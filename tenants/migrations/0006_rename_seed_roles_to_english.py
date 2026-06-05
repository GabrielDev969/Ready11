from django.db import migrations


def rename_seed_roles_to_english(apps, schema_editor):
    """Rename the pre-existing seed roles created with Portuguese names."""
    Role = apps.get_model('tenants', 'Role')
    Role.objects.filter(is_system_owner=True, name='Dono').update(name='Owner')
    Role.objects.filter(is_default=True, name='Membro da Equipe').update(name='Team Member')


def rename_seed_roles_to_portuguese(apps, schema_editor):
    Role = apps.get_model('tenants', 'Role')
    Role.objects.filter(is_system_owner=True, name='Owner').update(name='Dono')
    Role.objects.filter(is_default=True, name='Team Member').update(name='Membro da Equipe')


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0005_alter_role_name_alter_role_permissions_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_seed_roles_to_english, rename_seed_roles_to_portuguese),
    ]
