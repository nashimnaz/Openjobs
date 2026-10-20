import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import slugify


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the primary unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class RoleType(models.TextChoices):
    CANDIDATE = "CANDIDATE", "Candidate"
    EMPLOYER = "EMPLOYER", "Employer"
    ADMINISTRATOR = "ADMINISTRATOR", "Administrator"


class Role(models.Model):
    """
    Platform role representation (Candidate, Employer, Administrator).
    Allows fine-grained, backend-enforced permissions and multi-role assignments.
    """

    name = models.CharField(
        max_length=30,
        choices=RoleType.choices,
        unique=True,
        db_index=True,
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class User(AbstractUser):
    """
    Single central identity model for the entire OpenJobs platform.
    Used by Candidates, Employers, and Administrators.
    """

    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text="Optional public handle or identifier.",
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
        help_text="Primary email address used for login.",
    )
    phone_number = models.CharField(max_length=25, blank=True, null=True)
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether the email address has been verified.",
    )
    roles = models.ManyToManyField(
        Role,
        through="UserRole",
        related_name="users",
        blank=True,
        help_text="Platform roles assigned to this user.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.username:
            # Fallback username generated from email prefix or UUID if absent
            base = self.email.split("@")[0] if self.email else "user"
            self.username = f"{base}_{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def has_role(self, role_name: str) -> bool:
        """Check if the user has an active platform role."""
        if self.is_superuser:
            return True
        return self.user_roles.filter(
            role__name=role_name, is_active=True
        ).exists()

    @property
    def is_candidate(self) -> bool:
        return self.has_role(RoleType.CANDIDATE)

    @property
    def is_employer(self) -> bool:
        return self.has_role(RoleType.EMPLOYER)

    @property
    def is_platform_admin(self) -> bool:
        return self.is_staff or self.has_role(RoleType.ADMINISTRATOR)


class UserRole(models.Model):
    """
    Explicit joining model for Users and Roles.
    Supports multi-role membership with activation toggles.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_memberships"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Allows disabling a specific role without deleting the history.",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} -> {self.role.name} ({'Active' if self.is_active else 'Inactive'})"


class Organization(models.Model):
    """
    Foundation model for Employer Organizations.
    Supports multiple team members per company with tenant isolation.
    """

    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    website = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Verification status checked by platform administrators.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "org"
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class OrgMemberRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Administrator"
    RECRUITER = "RECRUITER", "Recruiter"
    MEMBER = "MEMBER", "Member"


class OrganizationMembership(models.Model):
    """
    Association between an Employer User and an Organization.
    Controls access to company-specific postings, candidate applications, and settings.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=20,
        choices=OrgMemberRole.choices,
        default=OrgMemberRole.MEMBER,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization Membership"
        verbose_name_plural = "Organization Memberships"
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user.email} @ {self.organization.name} ({self.role})"
