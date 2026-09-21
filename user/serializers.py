import datetime

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from user.models import Follow, Profile

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=5, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class LoginSerializer(serializers.Serializer):
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


class ProfileListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "email",
            "nickname",
            "bio",
            "photo",
        )
        read_only_fields = ("id",)


class ProfileDetailSerializer(ProfileListSerializer):
    age = serializers.IntegerField(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "email",
            "nickname",
            "date_of_birth",
            "bio",
            "gender",
            "photo",
            "age",
            "followers_count",
            "following_count",
        ]

    def validate_date_of_birth(self, value):
        if value > datetime.date.today():
            raise serializers.ValidationError(
                "Date of birth CANNOT be in the future"
            )
        return value


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.CharField(
        source="follower.email",
        read_only=True,
    )
    following_email = serializers.CharField(
        source="following.email",
        read_only=True,
    )

    class Meta:
        model = Follow
        fields = [
            "id",
            "follower",
            "following",
            "following_email",
            "created_at",
        ]
        extra_kwargs = {
            "following": {"write_only": False},
        }

    def validate_following(self, value):
        request = self.context.get("request")
        if request and value == request.user:
            raise serializers.ValidationError("You cannot follow yourself.")
        return value
