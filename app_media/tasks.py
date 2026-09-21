from celery import shared_task
from django.utils import timezone


@shared_task
def publish_scheduled_posts():

    from app_media.models import Hashtag, Post, ScheduledPost

    pending = ScheduledPost.objects.filter(
        publish_at__lte=timezone.now(),
        is_published=False,
    )

    for scheduled in pending:
        post = Post.objects.create(
            author=scheduled.author,
            content=scheduled.content,
            image=scheduled.image,
        )

        if scheduled.hashtags:
            for tag_name in scheduled.hashtags.split(","):
                tag, _ = Hashtag.objects.get_or_create(
                    name=tag_name.strip().lower()
                )
                post.hashtags.add(tag)

        scheduled.is_published = True
        scheduled.save()
