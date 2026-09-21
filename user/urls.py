from rest_framework.routers import DefaultRouter

from user.views import AuthViewSet, FollowViewSet, ProfileViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("profiles", ProfileViewSet, basename="profile")
router.register("follows", FollowViewSet, basename="follow")

urlpatterns = router.urls

app_name = "user"
