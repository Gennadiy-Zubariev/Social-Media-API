from rest_framework import serializers

from app_media.models import Comment, Hashtag, Post, ScheduledPost
from app_media.utils import parse_hashtags


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "name")


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.email", read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "author",
            "content",
            "created_at",
            "updated_at",
        )


class PostListSerializer(serializers.ModelSerializer):

    author = serializers.CharField(
        source="author.email",
        read_only=True,
    )
    hashtags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "image",
            "hashtags",
            "likes_count",
            "comments_count",
            "created_at",
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.email", read_only=True)
    hashtags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    comments = CommentSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "image",
            "hashtags",
            "comments",
            "likes_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]


class PostCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = [
            "id",
            "content",
            "image",
        ]

    def create(self, validated_data):
        post = Post.objects.create(**validated_data)
        tag_names = parse_hashtags(post.content)
        for name in tag_names:
            tag, _ = Hashtag.objects.get_or_create(name=name)
            post.hashtags.add(tag)
        return post

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if "content" in validated_data:
            instance.hashtags.clear()
            tag_names = parse_hashtags(instance.content)
            for name in tag_names:
                tag, _ = Hashtag.objects.get_or_create(name=name)
                instance.hashtags.add(tag)
        return instance


class ScheduledPostSerializer(serializers.ModelSerializer):

    author = serializers.CharField(
        source="author.email",
        read_only=True,
    )

    class Meta:
        model = ScheduledPost
        fields = [
            "id",
            "author",
            "content",
            "image",
            "hashtags",
            "publish_at",
            "is_published",
            "created_at",
        ]
        read_only_fields = ["is_published"]

    def validate_publish_at(self, value):
        from django.utils import timezone

        if value <= timezone.now():
            raise serializers.ValidationError(
                "Publish time must be in the future."
            )
        return value
