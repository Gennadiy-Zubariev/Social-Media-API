from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import renderers

from user.models import Follow, Profile
from user.permissions import IsProfileOwnerOrReadOnly
from user.serializers import (
    EmailAuthTokenSerializer,
    FollowerSerializer,
    FollowingSerializer,
    FollowSerializer,
    ProfileListSerializer,
    ProfileSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/users/register/ — публічна реєстрація нового користувача."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(ObtainAuthToken):
    """POST /api/users/login/ — {"email": ..., "password": ...} -> {"token": ...}."""

    serializer_class = EmailAuthTokenSerializer
    renderer_classes = [renderers.BrowsableAPIRenderer, renderers.JSONRenderer]


class LogoutView(APIView):
    """POST /api/users/logout/ — анулює токен поточного користувача."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=204)


class ProfileCreateView(generics.CreateAPIView):
    """POST /api/users/profiles/ — створити свій профіль (один раз)."""

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class MyProfileView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH /api/users/profiles/me/ — власний профіль."""

    queryset = Profile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsProfileOwnerOrReadOnly,
    ]

    def get_object(self):
        return get_object_or_404(Profile, user=self.request.user)


class ProfileDetailView(generics.RetrieveAPIView):
    """GET /api/users/profiles/<pk>/ — перегляд чужого профілю."""

    queryset = Profile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProfileListView(generics.ListAPIView):
    """GET /api/users/profiles/search/?search=... — пошук профілів за нікнеймом."""

    queryset = Profile.objects.select_related("user")
    serializer_class = ProfileListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nickname", "user__email"]


class FollowCreateView(generics.CreateAPIView):
    """POST /api/users/follows/ — {"following": <id>} підписатись на юзера."""

    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]


class FollowDestroyView(generics.DestroyAPIView):
    """DELETE /api/users/follows/<pk>/ — відписатись (pk запису Follow)."""

    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user)


class MyFollowersListView(generics.ListAPIView):
    """GET /api/users/follows/followers/ — хто підписаний на мене."""

    serializer_class = FollowerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(
            following=self.request.user
        ).select_related("follower__profile")


class MyFollowingListView(generics.ListAPIView):
    """GET /api/users/follows/following/ — на кого підписаний я."""

    serializer_class = FollowingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(
            follower=self.request.user
        ).select_related("following__profile")
