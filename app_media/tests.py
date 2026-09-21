from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app_media.models import Comment, Hashtag, Like, Post, ScheduledPost
from app_media.tasks import publish_scheduled_posts
from user.models import Follow

User = get_user_model()


def create_user(email="user@example.com"):
    return User.objects.create_user(email=email, password="pass12345")


class PostTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.other = create_user("other@example.com")
        self.client.force_authenticate(self.user)

    def test_create_post_parses_hashtags(self):
        response = self.client.post(
            reverse("app_media:post-list"),
            {"content": "Hello #Django and #api"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(id=response.data["id"])
        self.assertEqual(post.author, self.user)
        self.assertEqual(
            set(post.hashtags.values_list("name", flat=True)),
            {"django", "api"},
        )

    def test_filter_by_hashtag(self):
        tagged = Post.objects.create(author=self.user, content="a #django")
        tagged.hashtags.add(Hashtag.objects.create(name="django"))
        Post.objects.create(author=self.user, content="b")

        response = self.client.get(
            reverse("app_media:post-list"), {"hashtag": "Django"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([p["id"] for p in response.data], [tagged.id])

    def test_counts_are_correct_with_likes_and_comments(self):
        post = Post.objects.create(author=self.user, content="x")
        for i in range(2):
            Like.objects.create(
                user=create_user(f"l{i}@example.com"), post=post
            )
        for i in range(3):
            Comment.objects.create(
                author=self.other, post=post, content=f"c{i}"
            )

        response = self.client.get(reverse("app_media:post-list"))

        self.assertEqual(response.data[0]["likes_count"], 2)
        self.assertEqual(response.data[0]["comments_count"], 3)

    def test_update_own_post(self):
        post = Post.objects.create(author=self.user, content="old")

        response = self.client.put(
            reverse("app_media:post-detail", args=[post.id]),
            {"content": "new #tag"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.content, "new #tag")
        self.assertEqual(post.hashtags.get().name, "tag")

    def test_cannot_delete_foreign_post(self):
        post = Post.objects.create(author=self.other, content="x")

        response = self.client.delete(
            reverse("app_media:post-detail", args=[post.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(id=post.id).exists())

    def test_delete_own_post(self):
        post = Post.objects.create(author=self.user, content="x")

        response = self.client.delete(
            reverse("app_media:post-detail", args=[post.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_my_posts(self):
        mine = Post.objects.create(author=self.user, content="mine")
        Post.objects.create(author=self.other, content="theirs")

        response = self.client.get(reverse("app_media:post-my"))

        self.assertEqual([p["id"] for p in response.data], [mine.id])

    def test_feed_contains_only_followed_authors(self):
        Follow.objects.create(follower=self.user, following=self.other)
        followed = Post.objects.create(author=self.other, content="feed")
        Post.objects.create(author=self.user, content="mine")

        response = self.client.get(reverse("app_media:post-feed"))

        self.assertEqual([p["id"] for p in response.data], [followed.id])

    def test_like_toggle(self):
        post = Post.objects.create(author=self.other, content="x")
        url = reverse("app_media:post-like", args=[post.id])

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data, {"status": "liked"})
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data, {"status": "unliked"})
        self.assertFalse(Like.objects.exists())

    def test_liked_posts_list(self):
        liked = Post.objects.create(author=self.other, content="liked")
        Post.objects.create(author=self.other, content="not liked")
        Like.objects.create(user=self.user, post=liked)

        response = self.client.get(reverse("app_media:liked-list"))

        self.assertEqual([p["id"] for p in response.data], [liked.id])

    def test_post_detail_includes_comments_and_is_liked(self):
        post = Post.objects.create(author=self.other, content="x")
        Comment.objects.create(author=self.other, post=post, content="hi")
        Like.objects.create(user=self.user, post=post)

        response = self.client.get(
            reverse("app_media:post-detail", args=[post.id])
        )

        self.assertEqual(len(response.data["comments"]), 1)
        self.assertTrue(response.data["is_liked"])

    def test_posts_require_authentication(self):
        self.client.force_authenticate(None)

        response = self.client.get(reverse("app_media:post-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CommentTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.other = create_user("other@example.com")
        self.post = Post.objects.create(author=self.other, content="x")
        self.client.force_authenticate(self.user)
        self.list_url = reverse(
            "app_media:post-comments-list", args=[self.post.id]
        )

    def test_create_comment(self):
        response = self.client.post(self.list_url, {"content": "nice"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)

    def test_list_comments_only_for_this_post(self):
        Comment.objects.create(author=self.user, post=self.post, content="a")
        other_post = Post.objects.create(author=self.other, content="y")
        Comment.objects.create(author=self.user, post=other_post, content="b")

        response = self.client.get(self.list_url)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["content"], "a")

    def test_cannot_edit_foreign_comment(self):
        comment = Comment.objects.create(
            author=self.other, post=self.post, content="a"
        )

        response = self.client.patch(
            reverse(
                "app_media:post-comments-detail",
                args=[self.post.id, comment.id],
            ),
            {"content": "hacked"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_comment(self):
        comment = Comment.objects.create(
            author=self.user, post=self.post, content="a"
        )

        response = self.client.delete(
            reverse(
                "app_media:post-comments-detail",
                args=[self.post.id, comment.id],
            )
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ScheduledPostTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_create_scheduled_post(self):
        publish_at = timezone.now() + timedelta(hours=1)

        response = self.client.post(
            reverse("app_media:scheduled-list"),
            {"content": "later", "publish_at": publish_at.isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ScheduledPost.objects.get().author, self.user)

    def test_publish_at_in_past_rejected(self):
        publish_at = timezone.now() - timedelta(hours=1)

        response = self.client.post(
            reverse("app_media:scheduled-list"),
            {"content": "late", "publish_at": publish_at.isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_shows_only_own_unpublished(self):
        future = timezone.now() + timedelta(hours=1)
        mine = ScheduledPost.objects.create(
            author=self.user, content="mine", publish_at=future
        )
        ScheduledPost.objects.create(
            author=create_user("other@example.com"),
            content="theirs",
            publish_at=future,
        )
        ScheduledPost.objects.create(
            author=self.user,
            content="done",
            publish_at=future,
            is_published=True,
        )

        response = self.client.get(reverse("app_media:scheduled-list"))

        self.assertEqual([p["id"] for p in response.data], [mine.id])


class PublishScheduledPostsTaskTests(APITestCase):
    def test_publishes_due_posts_with_hashtags(self):
        user = create_user()
        due = ScheduledPost.objects.create(
            author=user,
            content="due",
            hashtags="Python, django",
            publish_at=timezone.now() - timedelta(minutes=1),
        )
        future = ScheduledPost.objects.create(
            author=user,
            content="future",
            publish_at=timezone.now() + timedelta(hours=1),
        )

        publish_scheduled_posts()

        due.refresh_from_db()
        future.refresh_from_db()
        self.assertTrue(due.is_published)
        self.assertFalse(future.is_published)
        post = Post.objects.get()
        self.assertEqual(post.content, "due")
        self.assertEqual(
            set(post.hashtags.values_list("name", flat=True)),
            {"python", "django"},
        )
