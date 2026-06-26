import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

import apps.audit.actions as audit_actions
from apps.audit.services import log_action
from apps.notifications.services import create_invite_notification, delete_invite_notifications

from .decorators import tenant_permission_required
from .forms import EmployeeSetupForm, GenesisSetupForm, RoleForm, TeamInviteForm, WorkspaceSettingsForm
from .models import (
    PERMISSION_GROUPS,
    InviteStatus,
    Role,
    WorkspaceInvite,
    WorkspaceMembership,
    default_expiration,
)
from .services import create_workspace
from .utils import tenant_permission_set, workspace_home_url

User = get_user_model()
logger = logging.getLogger(__name__)


def _send_invite_email(request, invite):
    """Send (or resend) the team invitation email with an absolute, scheme-aware link."""
    link = request.build_absolute_uri(f"/accept-invite/{invite.token}/")
    subject = _("Invitation to join %(workspace)s") % {'workspace': invite.workspace.name}
    message = _(
        "Hi!\n\nYou were invited by %(inviter)s to join the %(workspace)s "
        "workspace as %(role)s.\n\nClick the link to accept (valid for 24 hours):\n\n%(link)s"
    ) % {
        'inviter': request.user.first_name,
        'workspace': invite.workspace.name,
        'role': invite.role.name,
        'link': link,
    }
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [invite.email], fail_silently=False)

    # If the invited email already has an account, also surface an in-app invite
    # notification (Accept/Decline) so they don't need the email link.
    create_invite_notification(invite)


def genesis_setup_view(request, token):
    invite = get_object_or_404(WorkspaceInvite, token=token)

    # Lazily mark expired invites, then block any link that is no longer usable
    # (expired, cancelled or already accepted).
    if invite.status == InviteStatus.PENDING and invite.is_expired:
        invite.expire()
    if not invite.is_usable:
        return render(request, 'tenants/invite_unavailable.html', status=410)

    if request.method == 'POST':
        form = GenesisSetupForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            try:
                with transaction.atomic():
                    user, created = User.objects.get_or_create(
                        email=invite.email,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'is_active': True,
                            'email_verified': True,
                        }
                    )

                    if created:
                        user.set_password(password)
                        user.save()

                    workspace = create_workspace(company_name, user, request=request)

                    invite.status = InviteStatus.ACCEPTED
                    invite.save()

            except Exception:
                logger.exception("Failed to provision workspace from genesis invite %s", invite.pk)
                messages.error(request, _("Something went wrong while provisioning your workspace. Please try again."))
            else:
                login(request, user)
                return render(request, 'tenants/genesis_success.html', {
                    'workspace': workspace,
                    'workspace_url': workspace_home_url(request, workspace),
                })
    else:
        form = GenesisSetupForm()

    return render(request, 'tenants/genesis_setup.html', {'form': form, 'invite': invite})


@tenant_permission_required()
def tenant_home_view(request):
    """
    Workspace home. Accessible to ANY member, regardless of role — this is the
    safe landing so a user with no permissions still has somewhere to go. Shows
    system-wide update notifications.
    """
    workspace = request.tenant
    return render(request, 'tenants/home.html', {'workspace': workspace})


@tenant_permission_required()
def tenant_dashboard_view(request):
    workspace = request.tenant
    context = {
        'workspace_name': workspace.name,
    }
    return render(request, 'tenants/dashboard.html', context)


@tenant_permission_required('users.view')
def team_list_view(request):
    workspace = request.tenant

    # select_related('role') avoids N+1 queries on the listing.
    members = WorkspaceMembership.objects.filter(workspace=workspace).select_related('user', 'role')

    pending_invites = WorkspaceInvite.objects.filter(
        workspace=workspace,
        status=InviteStatus.PENDING,
    ).select_related('role').order_by('-created_at')

    # Pass the workspace so the form lists only this workspace's roles.
    form = TeamInviteForm(workspace=workspace)

    # Inviting requires at least one assignable (non-owner) role to exist.
    has_invitable_role = Role.objects.filter(workspace=workspace, is_system_owner=False).exists()

    context = {
        'members': members,
        'pending_invites': pending_invites,
        'form': form,
        'has_invitable_role': has_invitable_role,
    }
    return render(request, 'tenants/team_list.html', context)


@tenant_permission_required('users.invite')
def team_invite_view(request):
    workspace = request.tenant

    # Assigning a role requires being able to see roles. Without 'roles.view' the
    # inviter can't pick a role, so they can't send the invite — this prevents
    # handing out roles you have no visibility/authority over (privilege escalation).
    perms, _is_owner = tenant_permission_set(request)
    if 'roles.view' not in perms:
        messages.error(request, _("You need permission to view roles before you can assign one. Ask an administrator."))
        return redirect('team_list')

    if request.method == 'POST':
        form = TeamInviteForm(request.POST, workspace=workspace)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.workspace = workspace
            invite.invited_by = request.user
            invite.save()

            _send_invite_email(request, invite)
            log_action(request.user, audit_actions.MEMBER_INVITED, resource=invite,
                       detail={'email': invite.email, 'role': invite.role.name}, request=request)
            messages.success(request, _("Invitation sent to %(email)s.") % {'email': invite.email})
        else:
            messages.error(request, _("Could not send the invitation. Please check the data."))

    return redirect('team_list')


@tenant_permission_required('users.remove')
def member_remove_view(request, membership_id):
    """Remove a member from the workspace (their membership), with guardrails."""
    if request.method != 'POST':
        return redirect('team_list')

    workspace = request.tenant
    membership = get_object_or_404(
        WorkspaceMembership.objects.select_related('user', 'role'),
        id=membership_id,
        workspace=workspace,
    )

    # Guardrails: never remove the workspace owner, and don't let someone remove
    # themselves here (leaving a workspace would be a separate, explicit action).
    if membership.role.is_system_owner or membership.user_id == workspace.owner_id:
        messages.error(request, _("The workspace owner cannot be removed."))
        return redirect('team_list')

    if membership.user_id == request.user.id:
        messages.error(request, _("You cannot remove yourself."))
        return redirect('team_list')

    removed_user = membership.user
    email = removed_user.email

    with transaction.atomic():
        # Clear their default workspace if it pointed here (avoids a stale default).
        if removed_user.default_workspace_id == workspace.id:
            removed_user.default_workspace = None
            removed_user.save(update_fields=['default_workspace'])
        membership.delete()

    log_action(request.user, audit_actions.MEMBER_REMOVED,
               detail={'email': email}, request=request)
    messages.success(request, _("%(email)s was removed from the workspace.") % {'email': email})
    return redirect('team_list')


@tenant_permission_required()
def workspace_leave_view(request):
    """Let any member leave the current workspace on their own (owner can't)."""
    if request.method != 'POST':
        return redirect('tenant_home')

    workspace = request.tenant
    user = request.user

    # The owner must transfer ownership before leaving (out of scope for now).
    if user.id == workspace.owner_id:
        messages.error(request, _("The owner can't leave the workspace. Transfer ownership first."))
        return redirect('tenant_home')

    with transaction.atomic():
        if user.default_workspace_id == workspace.id:
            user.default_workspace = None
            user.save(update_fields=['default_workspace'])
        WorkspaceMembership.objects.filter(workspace=workspace, user=user).delete()

    log_action(user, audit_actions.MEMBER_LEFT,
               detail={'email': user.email, 'workspace': workspace.name}, request=request)
    messages.success(request, _("You left %(workspace)s.") % {'workspace': workspace.name})

    # Send them back to the public landing (they no longer belong here).
    host = request.get_host()
    port = f":{host.split(':')[1]}" if ':' in host else ''
    return redirect(f"{request.scheme}://{settings.TENANT_BASE_DOMAIN}{port}/")


@tenant_permission_required('users.invite')
def invite_cancel_view(request, invite_id):
    """Cancel a pending invite (revokes its link)."""
    if request.method != 'POST':
        return redirect('team_list')

    invite = get_object_or_404(WorkspaceInvite, id=invite_id, workspace=request.tenant)
    if invite.status == InviteStatus.PENDING:
        invite.cancel()
        # Remove the invite notification from the invited person right away.
        delete_invite_notifications(invite)
        log_action(request.user, audit_actions.INVITE_CANCELLED, resource=invite,
                   detail={'email': invite.email}, request=request)
        messages.success(request, _("Invitation to %(email)s cancelled.") % {'email': invite.email})
    else:
        messages.error(request, _("This invitation cannot be cancelled."))

    return redirect('team_list')


@tenant_permission_required('users.invite')
def invite_resend_view(request, invite_id):
    """Resend an invite, generating a brand-new token and a fresh 24h window."""
    if request.method != 'POST':
        return redirect('team_list')

    invite = get_object_or_404(WorkspaceInvite, id=invite_id, workspace=request.tenant)
    if invite.status in (InviteStatus.ACCEPTED, InviteStatus.CANCELLED):
        messages.error(request, _("This invitation cannot be resent."))
        return redirect('team_list')

    # New token invalidates the previous link; reset status and expiration window.
    invite.token = uuid.uuid4()
    invite.status = InviteStatus.PENDING
    invite.expires_at = default_expiration()
    invite.save(update_fields=['token', 'status', 'expires_at'])

    _send_invite_email(request, invite)
    log_action(request.user, audit_actions.INVITE_RESENT, resource=invite,
               detail={'email': invite.email}, request=request)
    messages.success(request, _("Invitation resent to %(email)s.") % {'email': invite.email})
    return redirect('team_list')


def accept_invite_view(request, token):
    workspace = request.tenant
    invite = get_object_or_404(WorkspaceInvite, token=token, workspace=workspace)

    # Lazily mark expired invites, then block any link that is no longer usable
    # (expired, cancelled or already accepted).
    if invite.status == InviteStatus.PENDING and invite.is_expired:
        invite.expire()
    if not invite.is_usable:
        return render(request, 'tenants/invite_unavailable.html', status=410)

    user_exists = User.objects.filter(email=invite.email).exists()

    if request.method == 'POST':
        if user_exists:
            # Existing accounts must be authenticated as the invited email before
            # being added to the workspace. Possession of the link is not enough.
            if not request.user.is_authenticated:
                messages.info(request, _("Please log in to accept this invitation."))
                return redirect(f"{reverse('login')}?next={request.get_full_path()}")

            if request.user.email.lower() != invite.email.lower():
                messages.error(request, _("This invitation was sent to a different account."))
                return redirect('login')

            user = request.user
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=user,
                defaults={'role': invite.role},
            )
            # First workspace a user joins becomes their default.
            if user.default_workspace is None:
                user.default_workspace = workspace
                user.save(update_fields=['default_workspace'])

            invite.status = InviteStatus.ACCEPTED
            invite.save()

            log_action(user, audit_actions.MEMBER_JOINED, resource=invite,
                       detail={'email': user.email, 'role': invite.role.name}, request=request)
            messages.success(request, _("You have joined %(workspace)s.") % {'workspace': workspace.name})
            return redirect('tenant_home')

        else:
            form = EmployeeSetupForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        user = User.objects.create(
                            email=invite.email,
                            first_name=form.cleaned_data['first_name'],
                            last_name=form.cleaned_data['last_name'],
                            is_active=True,
                            email_verified=True,
                        )
                        user.set_password(form.cleaned_data['password'])

                        user.default_workspace = workspace
                        user.save()

                        WorkspaceMembership.objects.create(
                            workspace=workspace,
                            user=user,
                            role=invite.role,
                        )

                        invite.status = InviteStatus.ACCEPTED
                        invite.save()

                        log_action(user, audit_actions.MEMBER_JOINED, resource=invite,
                                   detail={'email': user.email, 'role': invite.role.name}, request=request)
                        login(request, user)
                        return redirect('tenant_home')

                except Exception:
                    logger.exception("Failed to accept invite %s for new user", invite.pk)
                    messages.error(request, _("Something went wrong while processing your invitation. Please try again."))
    else:
        form = EmployeeSetupForm() if not user_exists else None

    context = {
        'invite': invite,
        'form': form,
        'user_exists': user_exists,
        'workspace': workspace,
    }
    return render(request, 'tenants/accept_invite.html', context)


@tenant_permission_required('roles.view')
def role_list_view(request):
    workspace = request.tenant
    roles = (
        Role.objects
        .filter(workspace=workspace)
        .annotate(member_count=Count('members'))
        .order_by('-is_system_owner', 'name')
    )
    return render(request, 'tenants/role_list.html', {'roles': roles})


@tenant_permission_required('roles.create')
def role_create_view(request):
    workspace = request.tenant

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.workspace = workspace

            # If this role is marked as default, unset the previous default.
            if role.is_default:
                Role.objects.filter(workspace=workspace, is_default=True).update(is_default=False)

            role.permissions = form.cleaned_data['permissions']
            role.save()

            log_action(request.user, audit_actions.ROLE_CREATED, resource=role,
                       detail={'name': role.name}, request=request)
            messages.success(request, _("Role '%(name)s' created.") % {'name': role.name})
            return redirect('role_list')
    else:
        form = RoleForm()

    return render(request, 'tenants/role_form.html', {
        'form': form,
        'permission_groups': PERMISSION_GROUPS,
        'selected_permissions': form['permissions'].value() or [],
    })


@tenant_permission_required('roles.edit')
def role_update_view(request, role_id):
    workspace = request.tenant
    role = get_object_or_404(Role, id=role_id, workspace=workspace)

    # The absolute owner role is locked.
    if role.is_system_owner:
        messages.error(request, _("The owner role cannot be edited."))
        return redirect('role_list')

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            role = form.save(commit=False)

            if role.is_default:
                Role.objects.filter(workspace=workspace, is_default=True).exclude(pk=role.pk).update(is_default=False)

            role.permissions = form.cleaned_data['permissions']
            role.save()

            log_action(request.user, audit_actions.ROLE_UPDATED, resource=role,
                       detail={'name': role.name}, request=request)
            messages.success(request, _("Role '%(name)s' updated.") % {'name': role.name})
            return redirect('role_list')
    else:
        form = RoleForm(instance=role, initial={'permissions': role.permissions})

    return render(request, 'tenants/role_form.html', {
        'form': form,
        'role': role,
        'permission_groups': PERMISSION_GROUPS,
        'selected_permissions': form['permissions'].value() or [],
    })


@tenant_permission_required('roles.delete')
def role_delete_view(request, role_id):
    workspace = request.tenant
    role = get_object_or_404(Role, id=role_id, workspace=workspace)

    if request.method != 'POST':
        return redirect('role_list')

    # Guardrails: never delete the owner role, nor a role still assigned to members.
    if role.is_system_owner:
        messages.error(request, _("The owner role cannot be deleted."))
        return redirect('role_list')

    if role.members.exists():
        messages.error(request, _("This role can't be deleted while members are using it."))
        return redirect('role_list')

    name = role.name
    role.delete()
    log_action(request.user, audit_actions.ROLE_DELETED,
               detail={'name': name}, request=request)
    messages.success(request, _("Role '%(name)s' deleted.") % {'name': name})
    return redirect('role_list')


@tenant_permission_required('tenant.update')
def workspace_settings_view(request):
    workspace = request.tenant
    form = WorkspaceSettingsForm(instance=workspace)

    if request.method == 'POST':
        form = WorkspaceSettingsForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            log_action(request.user, audit_actions.WORKSPACE_UPDATED,
                       resource=workspace,
                       detail={'name': workspace.name, 'timezone': workspace.timezone},
                       request=request)
            messages.success(request, _("Workspace settings saved."))
            return redirect('workspace_settings')

    return render(request, 'tenants/workspace_settings.html', {
        'workspace': workspace,
        'form': form,
    })
