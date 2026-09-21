from celery import shared_task
from django.utils import timezone

from app_media.utils import parse_hashtags


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
        tag_names = set(parse_hashtags(scheduled.content))
        if scheduled.hashtags:
            tag_names.update(
                t.strip().lower().lstrip("#")
                for t in scheduled.hashtags.split(",")
                if t.strip()
            )

        for name in tag_names:
            tag, _ = Hashtag.objects.get_or_create(name=name)
            post.hashtags.add(tag)

        scheduled.is_published = True
        scheduled.save()
