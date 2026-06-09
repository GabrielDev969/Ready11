from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from tenants.models import InviteStatus, WorkspaceMembership
from tenants.utils import workspace_home_url

from .models import Notification, NotificationType
from .services import mark_all_read, mark_read, recent_notifications


def notification_list(request):
    """Full notifications page (also the hub for users with no workspace)."""
    if not request.user.is_authenticated:
        return redirect('login')

    notifications = list(
        Notification.objects.visible_to(request.user).select_related('workspace', 'invite', 'invite__role')[:100]
    )
    read_ids = set(request.user.notification_reads.values_list('notification_id', flat=True))
    for n in notifications:
        n.unread = n.id not in read_ids

    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'has_workspace': WorkspaceMembership.objects.filter(user=request.user).exists(),
    })


def notifications_feed(request):
    """Live feed for the bell: rendered recent items + unread count (JSON)."""
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'auth required'}, status=401)

    recent, unread_count = recent_notifications(request.user)
    html = render_to_string(
        'partials/notification_bell_items.html',
        {'notif_recent': recent},
        request=request,
    )
    return JsonResponse({'unread': unread_count, 'html': html})


def notification_detail(request, notification_id):
    """Show the full content of a notification (non-invite); marks it read."""
    if not request.user.is_authenticated:
        return redirect('login')

    notification = get_object_or_404(Notification.objects.visible_to(request.user), id=notification_id)

    # Invites are action-only (Accept/Decline) — no detail page.
    if notification.notification_type == NotificationType.INVITE:
        return redirect('notifications')

    mark_read(request.user, notification)
    return render(request, 'notifications/detail.html', {'notification': notification})


def mark_read_view(request, notification_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        notification = get_object_or_404(Notification.objects.visible_to(request.user), id=notification_id)
        mark_read(request.user, notification)
    return redirect('notifications')


def mark_all_read_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        mark_all_read(request.user)
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect('notifications')


def invite_accept_view(request, notification_id):
    """Accept an invite straight from its notification (existing-account flow)."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return redirect('notifications')

    notification = get_object_or_404(
        Notification.objects.filter(recipient=request.user, notification_type='invite'),
        id=notification_id,
    )
    invite = notification.invite

    if invite is None or not invite.is_usable:
        mark_read(request.user, notification)
        messages.error(request, _("This invitation is no longer available."))
        return redirect('notifications')

    workspace = invite.workspace
    WorkspaceMembership.objects.get_or_create(
        workspace=workspace,
        user=request.user,
        defaults={'role': invite.role},
    )
    if request.user.default_workspace_id is None:
        request.user.default_workspace = workspace
        request.user.save(update_fields=['default_workspace'])

    invite.status = InviteStatus.ACCEPTED
    invite.save(update_fields=['status'])
    mark_read(request.user, notification)

    messages.success(request, _("You have joined %(workspace)s.") % {'workspace': workspace.name})
    return redirect(workspace_home_url(request, workspace) or 'notifications')


def invite_decline_view(request, notification_id):
    """Decline an invite from its notification."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return redirect('notifications')

    notification = get_object_or_404(
        Notification.objects.filter(recipient=request.user, notification_type='invite'),
        id=notification_id,
    )
    invite = notification.invite

    if invite is not None and invite.status == InviteStatus.PENDING:
        invite.status = InviteStatus.DECLINED
        invite.save(update_fields=['status'])
    mark_read(request.user, notification)

    messages.success(request, _("Invitation declined."))
    return redirect('notifications')
