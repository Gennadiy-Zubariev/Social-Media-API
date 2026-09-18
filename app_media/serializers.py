from django.utils import timezone
from rest_framework import serializers

from app_media.models import Comment, Hashtag, Like, Post, ScheduledPost
from app_media.tasks import publish_scheduled_post


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "name")


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.email", read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "content", "created_at", "updated_at")
        read_only_fields = ("id", "post", "author", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        validated_data["post"] = self.context["post"]
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.email", read_only=True)
    hashtag = HashtagSerializer(many=True, read_only=True)
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=255),
        write_only=True,
        required=False,
    )
    comments_count = serializers.IntegerField(
        source="comments.count", read_only=True
    )
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "content",
            "image",
            "hashtag",
            "hashtags",
            "comments_count",
            "likes_count",
            "is_liked",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def create(self, validated_data):
        hashtag_names = validated_data.pop("hashtags", [])
        validated_data["author"] = self.context["request"].user
        post = super().create(validated_data)
        self._set_hashtags(post, hashtag_names)
        return post

    def update(self, instance, validated_data):
        hashtag_names = validated_data.pop("hashtags", None)
        post = super().update(instance, validated_data)
        if hashtag_names is not None:
            self._set_hashtags(post, hashtag_names)
        return post

    @staticmethod
    def _set_hashtags(post, names):
        if not names:
            return
        hashtags = [
            Hashtag.objects.get_or_create(name=name.lower().strip("#"))[0]
            for name in names
        ]
        post.hashtag.set(hashtags)


class PostListSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = (
            "id",
            "author",
            "content",
            "image",
            "hashtag",
            "comments_count",
            "likes_count",
            "is_liked",
            "created_at",
        )


class LikeSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Like
        fields = ("id", "post", "user", "created_at")
        read_only_fields = ("id", "post", "user", "created_at")

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["post"] = self.context["post"]
        return super().create(validated_data)


class ScheduledPostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.email", read_only=True)

    class Meta:
        model = ScheduledPost
        fields = (
            "id",
            "author",
            "content",
            "image",
            "hashtags",
            "publish_at",
            "is_published",
            "created_at",
        )
        read_only_fields = ("id", "author", "is_published", "created_at")

    def validate_publish_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("publish_at must be in the future.")
        return value

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        scheduled_post = super().create(validated_data)
        publish_scheduled_post.apply_async(
            args=[scheduled_post.id], eta=scheduled_post.publish_at
        )
        return scheduled_post
