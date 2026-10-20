from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import (
    User,
    Role,
    UserRole,
    Organization,
    OrganizationMembership,
)


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "username",
        "first_name",
        "last_name",
        "is_email_verified",
        "is_staff",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_staff", "is_superuser", "is_active", "is_email_verified", "roles"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-created_at"]
    inlines = [UserRoleInline, OrganizationMembershipInline]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "username", "phone_number")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "website", "is_verified", "is_active", "created_at"]
    list_filter = ["is_verified", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationMembershipInline]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["user__email", "organization__name"]
