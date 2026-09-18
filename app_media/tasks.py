from celery import shared_task

from app_media.models import Hashtag, Post, ScheduledPost


@shared_task
def publish_scheduled_post(scheduled_post_id):
    try:
        scheduled_post = ScheduledPost.objects.get(
            pk=scheduled_post_id, is_published=False
        )
    except ScheduledPost.DoesNotExist:
        return

    post = Post.objects.create(
        author=scheduled_post.author,
        content=scheduled_post.content,
        image=scheduled_post.image or None,
    )

    hashtag_names = [
        name.strip()
        for name in scheduled_post.hashtags.split(",")
        if name.strip()
    ]
    if hashtag_names:
        hashtags = [
            Hashtag.objects.get_or_create(name=name.lower().strip("#"))[0]
            for name in hashtag_names
        ]
        post.hashtag.set(hashtags)

    scheduled_post.is_published = True
    scheduled_post.save(update_fields=["is_published"])
