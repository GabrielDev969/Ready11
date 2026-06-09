from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import render

from tenants.decorators import tenant_permission_required
from tenants.utils import tenant_permission_set
from .models import AuditLog


@tenant_permission_required()
def audit_log_list_view(request):
    _, is_owner = tenant_permission_set(request)
    if not is_owner and not request.user.is_staff:
        return HttpResponseForbidden()

    workspace = request.tenant
    logs_qs = AuditLog.objects.filter(
        workspace_schema=workspace.schema_name,
    ).select_related('user')

    paginator = Paginator(logs_qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'audit/log_list.html', {'page': page})
