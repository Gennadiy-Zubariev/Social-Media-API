from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from app_media.views import (
    CommentViewSet,
    LikedPostsViewSet,
    PostViewSet,
    ScheduledPostViewSet,
)

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register("liked", LikedPostsViewSet, basename="liked")
router.register("scheduled", ScheduledPostViewSet, basename="scheduled")

# /api/posts/{post_pk}/comments/
posts_router = NestedDefaultRouter(router, "posts", lookup="post")
posts_router.register("comments", CommentViewSet, basename="post-comments")

urlpatterns = router.urls + posts_router.urls

app_name = "app_media"
