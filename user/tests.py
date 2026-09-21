from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from user.models import Follow

User = get_user_model()


def create_user(email="user@example.com", password="pass12345"):
    return User.objects.create_user(email=email, password=password)


class AuthTests(APITestCase):
    def test_register_returns_token(self):
        response = self.client.post(
            reverse("user:auth-register"),
            {"email": "new@example.com", "password": "pass12345"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "new@example.com")
        self.assertTrue(
            Token.objects.filter(key=response.data["token"]).exists()
        )

    def test_register_creates_profile(self):
        self.client.post(
            reverse("user:auth-register"),
            {"email": "new@example.com", "password": "pass12345"},
        )

        user = User.objects.get(email="new@example.com")
        self.assertTrue(hasattr(user, "profile"))

    def test_register_short_password_rejected(self):
        response = self.client.post(
            reverse("user:auth-register"),
            {"email": "new@example.com", "password": "123"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        create_user()

        response = self.client.post(
            reverse("user:auth-login"),
            {"email": "user@example.com", "password": "pass12345"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_wrong_password(self):
        create_user()

        response = self.client.post(
            reverse("user:auth-login"),
            {"email": "user@example.com", "password": "wrong"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_deletes_token(self):
        user = create_user()
        self.client.force_authenticate(user)
        Token.objects.create(user=user)

        response = self.client.post(reverse("user:auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse("user:auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_me_returns_own_profile(self):
        response = self.client.get(reverse("user:profile-me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

    def test_me_patch_updates_profile(self):
        response = self.client.patch(
            reverse("user:profile-me"), {"nickname": "cool", "bio": "hi"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.nickname, "cool")
        self.assertEqual(self.user.profile.bio, "hi")

    def test_future_date_of_birth_rejected(self):
        response = self.client.patch(
            reverse("user:profile-me"), {"date_of_birth": "2999-01-01"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_by_nickname(self):
        self.user.profile.nickname = "alpha"
        self.user.profile.save()
        other = create_user("other@example.com")
        other.profile.nickname = "beta"
        other.profile.save()

        response = self.client.get(
            reverse("user:profile-list"), {"nickname": "alp"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nickname"], "alpha")

    def test_cannot_update_foreign_profile(self):
        other = create_user("other@example.com")

        response = self.client.patch(
            reverse("user:profile-detail", args=[other.profile.id]),
            {"bio": "hacked"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_requires_authentication(self):
        self.client.force_authenticate(None)

        response = self.client.get(reverse("user:profile-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FollowTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.other = create_user("other@example.com")
        self.client.force_authenticate(self.user)

    def test_follow_user(self):
        response = self.client.post(
            reverse("user:follow-list"), {"following": self.other.id}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Follow.objects.filter(
                follower=self.user, following=self.other
            ).exists()
        )

    def test_cannot_follow_self(self):
        response = self.client.post(
            reverse("user:follow-list"), {"following": self.user.id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_follow_twice(self):
        Follow.objects.create(follower=self.user, following=self.other)

        response = self.client.post(
            reverse("user:follow-list"), {"following": self.other.id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unfollow(self):
        follow = Follow.objects.create(
            follower=self.user, following=self.other
        )

        response = self.client.delete(
            reverse("user:follow-detail", args=[follow.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Follow.objects.exists())

    def test_followers_list(self):
        Follow.objects.create(follower=self.other, following=self.user)

        response = self.client.get(reverse("user:follow-followers"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["follower"], self.other.email)
