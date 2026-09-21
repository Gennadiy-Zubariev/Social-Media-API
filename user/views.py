from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from user.models import Follow, Profile
from user.permissions import IsOwnerOrReadOnly
from user.serializers import (
    FollowSerializer,
    LoginSerializer,
    ProfileDetailSerializer,
    ProfileListSerializer,
    UserRegisterSerializer,
)

User = get_user_model()


class AuthViewSet(viewsets.GenericViewSet):
    """
    Аутентифікація через Token.

    Endpoints:
        POST /api/user/auth/register/  — реєстрація, повертає токен
        POST /api/user/auth/login/     — логін, повертає токен
        POST /api/user/auth/logout/    — видаляє токен

    register та login доступні всім (AllowAny),
    logout — тільки автентифікованим (перевизначено на action).
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "register":
            return UserRegisterSerializer
        if self.action == "login":
            return LoginSerializer
        return None

    @action(detail=False, methods=["post"])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "email": user.email},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def logout(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Профілі користувачів.

    Endpoints:
        GET   /api/user/profiles/          — список (з пошуком ?nickname=...)
        GET   /api/user/profiles/{id}/     — деталі одного профілю
        PUT   /api/user/profiles/{id}/     — оновити (тільки власник)
        PATCH /api/user/profiles/{id}/     — часткове оновлення

    Без CreateModelMixin — профіль створюється автоматично через сигнал.
    Без DestroyModelMixin — профіль видаляється каскадно з User.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return ProfileListSerializer
        return ProfileDetailSerializer

    def get_queryset(self):
        queryset = Profile.objects.select_related("user").annotate(
            followers_count=Count("user__follower"),
            following_count=Count("user__following"),
        )

        nickname = self.request.query_params.get("nickname")
        if nickname:
            queryset = queryset.filter(nickname__icontains=nickname)

        return queryset

    @action(detail=False, methods=["get", "put", "patch", "delete"])
    def me(self, request):
        """
        GET    /api/profiles/me/  — мій профіль
        PUT    /api/profiles/me/  — оновити повністю
        PATCH  /api/profiles/me/  — часткове оновлення
        DELETE /api/profiles/me/  — видалити профіль
        """

        try:
            profile = self.get_queryset().get(user=request.user)
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "GET":
            serializer = ProfileDetailSerializer(profile)
            return Response(serializer.data)

        if request.method == "DELETE":
            profile.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ProfileDetailSerializer(
            profile,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="create-profile")
    def create_profile(self, request):
        """POST /api/profiles/create-profile/"""
        if hasattr(request.user, "profile"):
            return Response(
                {"error": "Profile already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ProfileDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FollowViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Підписки.

    Endpoints:
        GET    /api/user/follows/            — на кого я підписаний
        POST   /api/user/follows/            — підписатися (передати following: user_id)
        DELETE /api/user/follows/{id}/       — відписатися
        GET    /api/user/follows/followers/   — хто підписаний на мене

    perform_create автоматично підставляє follower = request.user,
    щоб юзер не міг створити підписку від чужого імені.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer

    def get_queryset(self):
        return Follow.objects.filter(
            follower=self.request.user
        ).select_related("follower", "following")

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    @action(detail=False, methods=["get"])
    def followers(self, request):
        followers = Follow.objects.filter(
            following=request.user
        ).select_related("follower")
        serializer = self.get_serializer(followers, many=True)
        return Response(serializer.data)
