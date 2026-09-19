from django.contrib import admin

from app_media.models import Comment, Hashtag, Like, Post, ScheduledPost


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content_short", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "author__email")

    def content_short(self, obj):
        return obj.content[:50]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "content_short", "created_at")

    def content_short(self, obj):
        return obj.content[:30]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ("author", "publish_at", "is_published")
    list_filter = ("is_published",)
