from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from apps.tenants.utils import effective_workspace, workspace_home_url


def landing(request):
    """
    Public marketing/presentation page served at the project root.

    On a tenant subdomain the root is not the marketing page: send authenticated
    users to their workspace home (Início) and anonymous users to the login screen.
    On the public domain, logged-in users get a button back to their workspace.
    """
    schema_name = getattr(getattr(request, 'tenant', None), 'schema_name', 'public')
    if schema_name != 'public':
        if request.user.is_authenticated:
            return redirect('tenant_home')
        return redirect('login')

    workspace_url = None
    if request.user.is_authenticated:
        workspace = effective_workspace(request.user)
        if workspace:
            workspace_url = workspace_home_url(request, workspace)

    return render(request, 'core/landing.html', {'workspace_url': workspace_url})


def healthz(request):
    """Lightweight liveness/readiness probe (checks DB connectivity)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)


def robots_txt(request):
    content = render_to_string('robots.txt')
    return HttpResponse(content, content_type='text/plain')


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)


def error_403(request, exception):
    return render(request, '403.html', status=403)
