from django.urls import path

from user.views import (
    FollowCreateView,
    FollowDestroyView,
    LoginView,
    LogoutView,
    MyFollowersListView,
    MyFollowingListView,
    MyProfileView,
    ProfileCreateView,
    ProfileDetailView,
    ProfileListView,
    RegisterView,
)

app_name = "user"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profiles/", ProfileCreateView.as_view(), name="profile-create"),
    path("profiles/me/", MyProfileView.as_view(), name="profile-me"),
    path("profiles/search/", ProfileListView.as_view(), name="profile-search"),
    path(
        "profiles/<int:pk>/",
        ProfileDetailView.as_view(),
        name="profile-detail",
    ),
    path("follows/", FollowCreateView.as_view(), name="follow-create"),
    path(
        "follows/followers/",
        MyFollowersListView.as_view(),
        name="my-followers",
    ),
    path(
        "follows/following/",
        MyFollowingListView.as_view(),
        name="my-following",
    ),
    path(
        "follows/<int:pk>/", FollowDestroyView.as_view(), name="follow-destroy"
    ),
]
