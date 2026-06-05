from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def landing(request):
    """
    Public marketing/presentation page served at the project root.

    On a tenant subdomain the root is not the marketing page: send authenticated
    users to their dashboard and anonymous users to the login screen.
    """
    schema_name = getattr(getattr(request, 'tenant', None), 'schema_name', 'public')
    if schema_name != 'public':
        if request.user.is_authenticated:
            return redirect('tenant_dashboard')
        return redirect('login')

    return render(request, 'core/landing.html')


def healthz(request):
    """Lightweight liveness/readiness probe (checks DB connectivity)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)
