from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from accounts.models import (
    User,
    Role,
    UserRole,
    RoleType,
    Organization,
    OrganizationMembership,
)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["name", "description"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "website",
            "is_verified",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "is_verified", "is_active", "created_at"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["organization", "role", "is_active", "created_at"]
        read_only_fields = ["created_at"]


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "is_email_verified",
            "roles",
            "organizations",
            "is_candidate",
            "is_employer",
            "is_platform_admin",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "is_email_verified",
            "roles",
            "organizations",
            "is_candidate",
            "is_employer",
            "is_platform_admin",
            "date_joined",
        ]

    def get_organizations(self, obj):
        memberships = obj.organization_memberships.filter(
            is_active=True, organization__is_active=True
        ).select_related("organization")
        return [
            {
                "id": m.organization.id,
                "name": m.organization.name,
                "slug": m.organization.slug,
                "role": m.role,
                "is_verified": m.organization.is_verified,
            }
            for m in memberships
        ]


class RegisterSerializer(serializers.Serializer):
    """
    Registration serializer enforcing password validation, email normalization,
    and safe initial role assignment (strictly Candidate or Employer).
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone_number = serializers.CharField(max_length=25, required=False, allow_blank=True, default="")
    role = serializers.ChoiceField(
        choices=[RoleType.CANDIDATE, RoleType.EMPLOYER],
        default=RoleType.CANDIDATE,
        help_text="Initial account type: CANDIDATE or EMPLOYER. Administrators cannot be self-registered.",
    )
    organization_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Required if registering as an employer.",
    )

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role", RoleType.CANDIDATE)
        org_name = attrs.get("organization_name", "").strip()

        if role == RoleType.EMPLOYER and not org_name:
            raise serializers.ValidationError(
                {"organization_name": "Organization name is required when registering as an Employer."}
            )
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        first_name = validated_data.get("first_name", "")
        last_name = validated_data.get("last_name", "")
        phone_number = validated_data.get("phone_number", "")
        role_type = validated_data.get("role", RoleType.CANDIDATE)
        org_name = validated_data.get("organization_name", "").strip()

        # 1. Create User
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )

        # 2. Assign initial platform role
        role_obj, _ = Role.objects.get_or_create(
            name=role_type,
            defaults={"description": f"Standard {role_type.lower()} access"},
        )
        UserRole.objects.create(user=user, role=role_obj, is_active=True)

        # 3. If employer, initialize their organization and set as OWNER
        if role_type == RoleType.EMPLOYER and org_name:
            org = Organization.objects.create(name=org_name)
            OrganizationMembership.objects.create(
                user=user,
                organization=org,
                role="OWNER",
                is_active=True,
            )

        return user


class LoginSerializer(serializers.Serializer):
    """
    Login serializer checking credentials securely against Django authentication.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This user account is inactive.")

        attrs["user"] = user
        return attrs
