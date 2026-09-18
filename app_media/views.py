from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.response import Response

from app_media.models import Comment, Hashtag, Like, Post, ScheduledPost
from app_media.permissions import IsAuthorOrReadOnly
from app_media.serializers import (
    CommentSerializer,
    HashtagSerializer,
    LikeSerializer,
    PostListSerializer,
    PostSerializer,
    ScheduledPostSerializer,
)
from user.models import Follow


def get_optimized_posts_queryset():
    """Базовий queryset постів з підвантаженими зв'язками (без N+1)."""
    return Post.objects.select_related("author").prefetch_related(
        "hashtag", "likes", "comments"
    )


class HashtagListView(generics.ListAPIView):
    """GET /api/media/hashtags/ — довідковий список хештегів."""

    queryset = Hashtag.objects.all()
    serializer_class = HashtagSerializer
    permission_classes = [permissions.IsAuthenticated]


class PostViewSet(viewsets.ModelViewSet):
    """Повний CRUD для постів: list/retrieve/create/update/destroy."""

    permission_classes = [permissions.IsAuthenticated, IsAuthorOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer

    def get_queryset(self):
        queryset = get_optimized_posts_queryset()
        hashtag = self.request.query_params.get("hashtag")

        if hashtag:
            queryset = queryset.filter(
                hashtag__name=hashtag.lower().strip("#")
            )

        return queryset.distinct()


class FeedListView(generics.ListAPIView):
    """GET /api/media/posts/feed/ — пости користувачів, на яких я підписаний."""

    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        following_ids = Follow.objects.filter(
            follower=self.request.user
        ).values_list("following_id", flat=True)
        return (
            get_optimized_posts_queryset()
            .filter(author_id__in=following_ids)
            .distinct()
        )


class LikedPostsListView(generics.ListAPIView):
    """GET /api/media/posts/liked/ — пости, які вподобав поточний юзер."""

    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_optimized_posts_queryset().filter(
            likes__user=self.request.user
        ).distinct()


class PostLikeView(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, generics.GenericAPIView
):
    """POST — лайкнути пост, DELETE — зняти лайк. Повного CRUD тут не треба."""

    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs["post_pk"])

    def get_queryset(self):
        return Like.objects.filter(post=self.get_post())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["post"] = self.get_post()
        return context

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        like = self.get_queryset().filter(user=request.user).first()
        if like is None:
            return Response({"detail": "Like not found."}, status=404)
        like.delete()
        return Response(status=204)


class PostCommentListCreateView(generics.ListCreateAPIView):
    """GET — список коментарів поста, POST — новий коментар."""

    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs["post_pk"])

    def get_queryset(self):
        return Comment.objects.filter(
            post=self.get_post()
        ).select_related("author")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["post"] = self.get_post()
        return context


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/media/comments/<pk>/ — власний коментар."""

    queryset = Comment.objects.select_related("author")
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrReadOnly]


class ScheduledPostViewSet(viewsets.ModelViewSet):
    """Повний CRUD запланованих постів — кожен юзер бачить лише свої."""

    serializer_class = ScheduledPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ScheduledPost.objects.filter(author=self.request.user)
