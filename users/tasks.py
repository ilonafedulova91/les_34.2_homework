from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.utils import timezone


@shared_task
def deactivate_inactive_users():
    User = get_user_model()

    cutoff_date = timezone.now() - relativedelta(months=1)

    updated_count = User.objects.filter(
        is_active=True,
        last_login__lt=cutoff_date,
    ).update(is_active=False)

    return f"Deactivated {updated_count} inactive users"
