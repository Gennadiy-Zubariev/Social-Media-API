from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from user.models import Follow, Profile

User = get_user_model()


class EmailAuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError(
                "Unable to log in with provided credentials."
            )
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ("id", "email", "password", "is_staff")
        read_only_fields = ("id", "is_staff")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    age = serializers.ReadOnlyField(source="get_age")

    class Meta:
        model = Profile
        fields = (
            "id",
            "email",
            "nickname",
            "gender",
            "date_of_birth",
            "age",
            "bio",
            "photo",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ProfileListSerializer(ProfileSerializer):
    class Meta(ProfileSerializer.Meta):
        fields = ("id", "email", "nickname", "photo")


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("id", "follower", "following", "created_at")
        read_only_fields = ("id", "follower", "created_at")

    def validate_following(self, value):
        request = self.context["request"]
        if value == request.user:
            raise serializers.ValidationError("You cannot follow yourself.")
        return value

    def create(self, validated_data):
        validated_data["follower"] = self.context["request"].user
        return super().create(validated_data)


class FollowerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="follower.email", read_only=True)
    nickname = serializers.CharField(
        source="follower.profile.nickname", read_only=True
    )

    class Meta:
        model = Follow
        fields = ("id", "email", "nickname", "created_at")


class FollowingSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="following.email", read_only=True)
    nickname = serializers.CharField(
        source="following.profile.nickname", read_only=True
    )

    class Meta:
        model = Follow
        fields = ("id", "email", "nickname", "created_at")
