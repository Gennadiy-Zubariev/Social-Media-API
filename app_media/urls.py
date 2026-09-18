from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app_media.views import (
    CommentDetailView,
    FeedListView,
    HashtagListView,
    LikedPostsListView,
    PostCommentListCreateView,
    PostLikeView,
    PostViewSet,
    ScheduledPostViewSet,
)

app_name = "app_media"

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register(
    "scheduled-posts", ScheduledPostViewSet, basename="scheduled-post"
)

urlpatterns = [
    path("hashtags/", HashtagListView.as_view(), name="hashtag-list"),
    path("posts/feed/", FeedListView.as_view(), name="post-feed"),
    path("posts/liked/", LikedPostsListView.as_view(), name="post-liked"),
    path(
        "posts/<int:post_pk>/like/",
        PostLikeView.as_view(),
        name="post-like",
    ),
    path(
        "posts/<int:post_pk>/comments/",
        PostCommentListCreateView.as_view(),
        name="post-comments",
    ),
    path(
        "comments/<int:pk>/", CommentDetailView.as_view(), name="comment-detail"
    ),
    path("", include(router.urls)),
]
