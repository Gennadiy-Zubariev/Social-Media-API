from django.conf import settings
from django.db import models


class Hashtag(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"#{self.name}"

    def save(self, *args, **kwargs):
        self.name = self.name.lower().strip("#")
        super().save(*args, **kwargs)


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    content = models.TextField()
    image = models.ImageField(upload_to="post_images/", null=True, blank=True)
    hashtags = models.ManyToManyField(
        Hashtag, related_name="posts", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.author} - {self.content[:30]}"


class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.post.id}: {self.content[:30]}"


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

    def __str__(self):
        return f"{self.user} ♥ {self.post.id}"


class ScheduledPost(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduled_posts",
    )
    content = models.TextField()
    image = models.ImageField(upload_to="scheduled/", blank=True, null=True)
    hashtags = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Comma-separated hashtags, e.g.: python,django,api",
    )
    publish_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["publish_at"]

    def __str__(self):
        status = "✓" if self.is_published else "⏳"
        return f"{status} {self.author}: {self.publish_at}"
