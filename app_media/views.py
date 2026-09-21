from django.db.models import Count, Exists, OuterRef
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app_media.models import Comment, Like, Post, ScheduledPost
from app_media.serializers import (
    CommentSerializer,
    PostCreateSerializer,
    PostDetailSerializer,
    PostListSerializer,
    ScheduledPostSerializer,
)
from user.permissions import IsOwnerOrReadOnly


class LikeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["liked", "unliked"])


@extend_schema(tags=["Posts"])
@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "hashtag", str, description="Фільтр за хештегом (без #)"
            )
        ]
    )
)
class PostViewSet(viewsets.ModelViewSet):
    """
    Пости.

    Endpoints:
        GET    /api/posts/              — всі пости (фільтр ?hashtag=django)
        POST   /api/posts/              — створити пост
        GET    /api/posts/{id}/         — деталі посту з коментарями
        PUT    /api/posts/{id}/         — оновити (тільки автор)
        DELETE /api/posts/{id}/         — видалити (тільки автор)
        GET    /api/posts/my/           — мої пости
        GET    /api/posts/feed/         — стрічка (пости підписок)
        POST   /api/posts/{id}/like/    — лайк / анлайк (toggle)

    annotate додає likes_count і comments_count одним запитом.
    Exists + OuterRef перевіряє чи поточний юзер лайкнув пост
    (для is_liked у detail серіалізаторі).
    """

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostCreateSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Post.objects.none()
        queryset = (
            Post.objects.select_related("author")
            .prefetch_related("hashtags", "comments__author")
            .annotate(
                likes_count=Count("likes"),
                comments_count=Count("comments"),
                is_liked=Exists(
                    Like.objects.filter(
                        post=OuterRef("pk"),
                        user=self.request.user,
                    )
                ),
            )
        )

        hashtag = self.request.query_params.get("hashtag")
        if hashtag:
            queryset = queryset.filter(hashtags__name=hashtag.lower())

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @extend_schema(responses=PostListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def my(self, request):
        posts = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(responses=PostListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def feed(self, request):
        following_ids = request.user.following.values_list(
            "following_id", flat=True
        )
        posts = self.get_queryset().filter(author_id__in=following_ids)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=None,
        responses={200: LikeStatusSerializer, 201: LikeStatusSerializer},
    )
    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post,
        )
        if not created:
            like.delete()
            return Response(
                {"status": "unliked"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": "liked"},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Comments"],
    parameters=[
        OpenApiParameter(
            "post_pk",
            int,
            OpenApiParameter.PATH,
            description="ID посту",
        )
    ],
)
class CommentViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Коментарі до посту (вкладений ресурс).

    Endpoints:
        GET    /api/posts/{post_pk}/comments/         — список
        POST   /api/posts/{post_pk}/comments/         — додати
        PUT    /api/posts/{post_pk}/comments/{id}/     — редагувати (автор)
        PATCH  /api/posts/{post_pk}/comments/{id}/     — часткове (автор)
        DELETE /api/posts/{post_pk}/comments/{id}/     — видалити (автор)

    post_pk приходить з URL через kwargs (NestedDefaultRouter).
    """

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    serializer_class = CommentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()
        return Comment.objects.filter(
            post_id=self.kwargs["post_pk"]
        ).select_related("author")

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            post_id=self.kwargs["post_pk"],
        )


@extend_schema(tags=["Liked"])
class LikedPostsViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/liked/ — пости, які поточний юзер лайкнув.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Post.objects.none()
        return (
            Post.objects.filter(likes__user=self.request.user)
            .select_related("author")
            .prefetch_related("hashtags")
            .annotate(
                likes_count=Count("likes"),
                comments_count=Count("comments"),
            )
        )


@extend_schema(tags=["Scheduled"])
class ScheduledPostViewSet(viewsets.ModelViewSet):
    """
    Відкладені пости (для Celery).

    Endpoints:
        GET    /api/scheduled/           — мої заплановані пости
        POST   /api/scheduled/           — створити
        GET    /api/scheduled/{id}/      — деталі
        PUT    /api/scheduled/{id}/      — оновити (поки не опубліковано)
        DELETE /api/scheduled/{id}/      — видалити

    Показує тільки пости поточного юзера.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ScheduledPostSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ScheduledPost.objects.none()
        return ScheduledPost.objects.filter(
            author=self.request.user, is_published=False
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
