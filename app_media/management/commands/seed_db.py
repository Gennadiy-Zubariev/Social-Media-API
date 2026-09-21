import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_media.models import Comment, Hashtag, Like, Post, ScheduledPost
from user.models import Follow, Profile

User = get_user_model()

SEED_DOMAIN = "seed.example.com"
SEED_PASSWORD = "password123"

BIOS = [
    "Люблю Python і каву.",
    "Backend-розробник.",
    "Фотографую міста.",
    "Читаю про космос.",
    "Бігаю зранку.",
]
TOPICS = ["django", "python", "api", "celery", "docker", "postgres", "rest"]
PHRASES = [
    "Сьогодні вивчаю",
    "Цікава стаття про",
    "Запустив проєкт з",
    "Порада дня:",
    "Довго розбирався з",
]
COMMENTS = ["Круто!", "Дякую за пост", "Згоден", "Цікаво, розкажи більше", "+1"]


class Command(BaseCommand):
    help = (
        "Наповнює базу тестовими даними: користувачі, профілі, підписки, "
        "пости, лайки, коментарі та відкладені пости."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=10, help="Кількість користувачів"
        )
        parser.add_argument(
            "--posts", type=int, default=3, help="Постів на користувача"
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Спочатку видалити раніше створені seed-дані",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = User.objects.filter(
                email__endswith=f"@{SEED_DOMAIN}"
            ).delete()
            self.stdout.write(f"Видалено записів: {deleted}")

        users = self._create_users(options["users"])
        self._fill_profiles(users)
        self._create_follows(users)
        posts = self._create_posts(users, options["posts"])
        self._create_likes_and_comments(users, posts)
        self._create_scheduled_posts(users)

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {len(users)} користувачів, {len(posts)} постів. "
                f"Логін: seed1@{SEED_DOMAIN} / {SEED_PASSWORD}"
            )
        )

    def _create_users(self, count):
        users = []
        for i in range(1, count + 1):
            email = f"seed{i}@{SEED_DOMAIN}"
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email, password=SEED_PASSWORD
                )
            users.append(user)
        return users

    def _fill_profiles(self, users):
        for i, user in enumerate(users, start=1):
            Profile.objects.filter(user=user).update(
                nickname=f"seed_user_{i}",
                bio=random.choice(BIOS),
                gender=random.choice(Profile.GenderChoice.values),
                date_of_birth=date.today()
                - timedelta(days=random.randint(18 * 365, 50 * 365)),
            )

    def _create_follows(self, users):
        for user in users:
            others = [u for u in users if u != user]
            targets = random.sample(others, k=min(3, len(others)))
            for target in targets:
                Follow.objects.get_or_create(follower=user, following=target)

    def _create_posts(self, users, per_user):
        posts = []
        for user in users:
            for _ in range(per_user):
                tags = random.sample(TOPICS, k=random.randint(1, 3))
                content = (
                    f"{random.choice(PHRASES)} "
                    + " ".join(f"#{tag}" for tag in tags)
                )
                post = Post.objects.create(author=user, content=content)
                for tag in tags:
                    hashtag, _ = Hashtag.objects.get_or_create(name=tag)
                    post.hashtags.add(hashtag)
                posts.append(post)
        return posts

    def _create_likes_and_comments(self, users, posts):
        for post in posts:
            likers = random.sample(users, k=random.randint(0, len(users)))
            for user in likers:
                Like.objects.get_or_create(user=user, post=post)
            for user in random.sample(users, k=random.randint(0, 3)):
                Comment.objects.create(
                    author=user,
                    post=post,
                    content=random.choice(COMMENTS),
                )

    def _create_scheduled_posts(self, users):
        for user in users[:3]:
            ScheduledPost.objects.create(
                author=user,
                content="Відкладений пост #scheduled",
                hashtags="scheduled",
                publish_at=timezone.now()
                + timedelta(hours=random.randint(1, 48)),
            )
