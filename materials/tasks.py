from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Course, Subscription


@shared_task
def test_celery_task():
    return "Celery is working!"


@shared_task
def send_course_update_notification(course_id):
    course = Course.objects.get(pk=course_id)

    subscriber_emails = list(
        Subscription.objects.filter(
            course=course,
            user__is_active=True,
        )
        .exclude(user__email="")
        .values_list("user__email", flat=True)
        .distinct()
    )

    if not subscriber_emails:
        return "No subscribers to notify."

    send_mail(
        subject=f"Course updated: {course.title}",
        message=(
            f'The course "{course.title}" has been updated.\n\n'
            "Log in to the LMS platform to see the latest changes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=subscriber_emails,
        fail_silently=False,
    )

    return f"Notification sent to {len(subscriber_emails)} subscribers."
