from rest_framework import permissions
from accounts.models import RoleType, OrgMemberRole


class IsCandidate(permissions.BasePermission):
    """
    Permission check strictly enforced on the backend:
    Allows access only to authenticated users with an active CANDIDATE role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_candidate
        )


class IsEmployer(permissions.BasePermission):
    """
    Permission check strictly enforced on the backend:
    Allows access only to authenticated users with an active EMPLOYER role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_employer
        )


class IsPlatformAdmin(permissions.BasePermission):
    """
    Permission check strictly enforced on the backend:
    Allows access only to administrators (staff, superuser, or ADMINISTRATOR role).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_platform_admin
        )


class IsOrganizationMember(permissions.BasePermission):
    """
    Object-level permission ensuring an employer can only access records
    belonging to an organization where they hold an active membership.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.is_superuser:
            return True

        # Supports checking objects with an 'organization' attribute or Organization instances themselves
        target_org = getattr(obj, "organization", obj)
        return request.user.organization_memberships.filter(
            organization=target_org, is_active=True
        ).exists()


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Ensures the user has an OWNER or ADMIN role within the target organization.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.is_superuser:
            return True

        target_org = getattr(obj, "organization", obj)
        return request.user.organization_memberships.filter(
            organization=target_org,
            role__in=[OrgMemberRole.OWNER, OrgMemberRole.ADMIN],
            is_active=True,
        ).exists()
