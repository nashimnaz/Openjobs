from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import (
    Role,
    RoleType,
    UserRole,
    Organization,
    OrganizationMembership,
    OrgMemberRole,
)
from accounts.permissions import (
    IsCandidate,
    IsEmployer,
    IsPlatformAdmin,
    IsOrganizationMember,
)

User = get_user_model()


class UserModelAndRoleTests(APITestCase):
    def setUp(self):
        # Ensure default roles exist
        self.candidate_role, _ = Role.objects.get_or_create(
            name=RoleType.CANDIDATE, defaults={"description": "Candidate"}
        )
        self.employer_role, _ = Role.objects.get_or_create(
            name=RoleType.EMPLOYER, defaults={"description": "Employer"}
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=RoleType.ADMINISTRATOR, defaults={"description": "Admin"}
        )

    def test_create_user_with_email_successful(self):
        user = User.objects.create_user(
            email="candidate@example.com",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Doe",
        )
        self.assertEqual(user.email, "candidate@example.com")
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.username)

    def test_create_user_email_normalized(self):
        user = User.objects.create_user(
            email="Test.User@EXAMPLE.COM",
            password="SecurePassword123!",
        )
        self.assertEqual(user.email, "test.user@example.com")

    def test_create_user_missing_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="password123")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@openjobs.dev",
            password="AdminPassword123!",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_platform_admin)

    def test_multi_role_support(self):
        user = User.objects.create_user(
            email="multi@example.com", password="Password123!"
        )
        self.assertFalse(user.is_candidate)
        self.assertFalse(user.is_employer)

        # Assign Candidate role
        UserRole.objects.create(user=user, role=self.candidate_role)
        self.assertTrue(user.is_candidate)
        self.assertFalse(user.is_employer)

        # Also assign Employer role (user holds multiple roles)
        UserRole.objects.create(user=user, role=self.employer_role)
        self.assertTrue(user.is_candidate)
        self.assertTrue(user.is_employer)

    def test_inactive_role_is_not_authorized(self):
        user = User.objects.create_user(
            email="inactive_role@example.com", password="Password123!"
        )
        UserRole.objects.create(
            user=user, role=self.candidate_role, is_active=False
        )
        self.assertFalse(user.is_candidate)


class BackendPermissionTests(APITestCase):
    def setUp(self):
        self.candidate_role, _ = Role.objects.get_or_create(
            name=RoleType.CANDIDATE
        )
        self.employer_role, _ = Role.objects.get_or_create(
            name=RoleType.EMPLOYER
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=RoleType.ADMINISTRATOR
        )

        self.candidate_user = User.objects.create_user(
            email="cand@example.com", password="Password123!"
        )
        UserRole.objects.create(user=self.candidate_user, role=self.candidate_role)

        self.employer_user = User.objects.create_user(
            email="emp@example.com", password="Password123!"
        )
        UserRole.objects.create(user=self.employer_user, role=self.employer_role)

        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="Password123!"
        )

    def test_is_candidate_permission(self):
        perm = IsCandidate()
        request = type("Request", (), {})()

        request.user = self.candidate_user
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.employer_user
        self.assertFalse(perm.has_permission(request, None))

    def test_is_employer_permission(self):
        perm = IsEmployer()
        request = type("Request", (), {})()

        request.user = self.employer_user
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.candidate_user
        self.assertFalse(perm.has_permission(request, None))

    def test_is_platform_admin_permission(self):
        perm = IsPlatformAdmin()
        request = type("Request", (), {})()

        request.user = self.admin_user
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.candidate_user
        self.assertFalse(perm.has_permission(request, None))


class OrganizationMembershipIsolationTests(APITestCase):
    def setUp(self):
        self.employer1 = User.objects.create_user(
            email="emp1@company-a.com", password="Password123!"
        )
        self.employer2 = User.objects.create_user(
            email="emp2@company-b.com", password="Password123!"
        )

        self.org_a = Organization.objects.create(name="Acme Corp")
        self.org_b = Organization.objects.create(name="Beta Industries")

        OrganizationMembership.objects.create(
            user=self.employer1, organization=self.org_a, role=OrgMemberRole.OWNER
        )
        OrganizationMembership.objects.create(
            user=self.employer2, organization=self.org_b, role=OrgMemberRole.OWNER
        )

    def test_organization_member_cannot_access_other_organization(self):
        perm = IsOrganizationMember()
        request = type("Request", (), {})()

        # Employer 1 accessing Org A -> Permitted
        request.user = self.employer1
        self.assertTrue(perm.has_object_permission(request, None, self.org_a))

        # Employer 1 attempting to access Org B -> Denied
        self.assertFalse(perm.has_object_permission(request, None, self.org_b))

        # Employer 2 accessing Org B -> Permitted
        request.user = self.employer2
        self.assertTrue(perm.has_object_permission(request, None, self.org_b))

        # Employer 2 attempting to access Org A -> Denied
        self.assertFalse(perm.has_object_permission(request, None, self.org_a))


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        Role.objects.get_or_create(name=RoleType.CANDIDATE)
        Role.objects.get_or_create(name=RoleType.EMPLOYER)
        Role.objects.get_or_create(name=RoleType.ADMINISTRATOR)

    def test_candidate_registration_success(self):
        url = reverse("auth-register")
        payload = {
            "email": "newcandidate@example.com",
            "password": "StrongPassword123!",
            "first_name": "Alice",
            "last_name": "Smith",
            "role": "CANDIDATE",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["email"], "newcandidate@example.com")
        self.assertTrue(response.data["user"]["is_candidate"])
        self.assertFalse(response.data["user"]["is_employer"])

    def test_employer_registration_creates_organization(self):
        url = reverse("auth-register")
        payload = {
            "email": "hiring@techcorp.com",
            "password": "StrongPassword123!",
            "first_name": "Bob",
            "last_name": "Recruiter",
            "role": "EMPLOYER",
            "organization_name": "Tech Corp",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["user"]["is_employer"])
        self.assertEqual(len(response.data["user"]["organizations"]), 1)
        self.assertEqual(
            response.data["user"]["organizations"][0]["name"], "Tech Corp"
        )
        self.assertEqual(
            response.data["user"]["organizations"][0]["role"], "OWNER"
        )

    def test_cannot_self_register_as_admin(self):
        url = reverse("auth-register")
        payload = {
            "email": "hacker@example.com",
            "password": "StrongPassword123!",
            "role": "ADMINISTRATOR",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_and_failure(self):
        User.objects.create_user(
            email="registered@example.com", password="CorrectPassword123!"
        )

        url = reverse("auth-login")

        # Wrong password
        bad_response = self.client.post(
            url,
            {"email": "registered@example.com", "password": "WrongPassword"},
            format="json",
        )
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct credentials
        good_response = self.client.post(
            url,
            {"email": "registered@example.com", "password": "CorrectPassword123!"},
            format="json",
        )
        self.assertEqual(good_response.status_code, status.HTTP_200_OK)
        self.assertIn("token", good_response.data)

    def test_user_profile_me_endpoint(self):
        user = User.objects.create_user(
            email="me@example.com", password="Password123!"
        )
        url = reverse("auth-me")

        # Unauthenticated -> 401
        res_unauth = self.client.get(url)
        self.assertEqual(res_unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated -> 200
        self.client.force_authenticate(user=user)
        res_auth = self.client.get(url)
        self.assertEqual(res_auth.status_code, status.HTTP_200_OK)
        self.assertEqual(res_auth.data["email"], "me@example.com")

    def test_logout_revokes_token(self):
        user = User.objects.create_user(
            email="logout@example.com", password="Password123!"
        )
        self.client.force_authenticate(user=user)
        login_url = reverse("auth-login")
        self.client.force_authenticate(user=None)

        # Login to generate token
        login_res = self.client.post(
            login_url,
            {"email": "logout@example.com", "password": "Password123!"},
            format="json",
        )
        token = login_res.data["token"]

        # Call logout with token
        logout_url = reverse("auth-logout")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        logout_res = self.client.post(logout_url)
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Calling /me with the revoked token should now fail
        me_url = reverse("auth-me")
        me_res = self.client.get(me_url)
        self.assertEqual(me_res.status_code, status.HTTP_401_UNAUTHORIZED)
