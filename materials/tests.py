from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import (APIRequestFactory, APITestCase,
                                 force_authenticate)

from users.models import User

from .models import Course, Lesson, Subscription
from .tasks import send_course_update_notification
from .views import CourseViewSet


class LessonTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="test_user@example.com",
            password="test_password",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test description",
            owner=self.user,
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Test Lesson",
            description="Test less description",
            video_url="https://www.youtube.com/watch?v=test123",
            owner=self.user,
        )

        self.client.force_authenticate(user=self.user)

    def test_lesson_retrieve(self):
        url = reverse("lesson-detail", args=[self.lesson.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.lesson.id)
        self.assertEqual(response.data["title"], "Test Lesson")

    def test_lesson_create(self):
        url = reverse("lesson-list-create")

        data = {
            "course": self.course.id,
            "title": "New Test Lesson",
            "description": "New test description",
            "video_url": "https://www.youtube.com/watch?v=new123",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Test Lesson")
        self.assertEqual(response.data["owner"], self.user.id)

    def test_lesson_update(self):
        url = reverse("lesson-detail", args=[self.lesson.id])

        data = {
            "course": self.course.id,
            "title": "Updated Test Lesson",
            "description": "Updated test description",
            "video_url": "https://www.youtube.com/watch?v=updated123",
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Test Lesson")
        self.assertEqual(response.data["description"], "Updated test description")

    def test_lesson_delete(self):
        url = reverse("lesson-detail", args=[self.lesson.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_lesson_update_by_another_user(self):
        another_user = User.objects.create_user(
            email="test_another_user@example.com",
            password="test_password",
        )

        self.client.force_authenticate(user=another_user)

        url = reverse("lesson-detail", args=[self.lesson.id])

        data = {
            "course": self.course.id,
            "title": "Not Updated Test Lesson",
            "description": "Not Updated test description",
            "video_url": "https://www.youtube.com/watch?v=test123",
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_moderator_cannot_create_lesson(self):
        moderator = User.objects.create_user(
            email="test_moderator@example.com",
            password="test_password",
        )

        moderator_group, _ = Group.objects.get_or_create(name="Moderator")
        moderator_group.user_set.add(moderator)

        self.client.force_authenticate(user=moderator)

        url = reverse("lesson-list-create")

        data = {
            "course": self.course.id,
            "title": "Test Moderator Lesson",
            "description": "Test Moderator description",
            "video_url": "https://www.youtube.com/watch?v=moderator123",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_lesson(self):
        moderator = User.objects.create_user(
            email="moderator_test@example.com",
            password="test_password",
        )

        moderator_group, _ = Group.objects.get_or_create(name="Moderator")
        moderator_group.user_set.add(moderator)

        self.client.force_authenticate(user=moderator)

        url = reverse("lesson-detail", args=[self.lesson.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_moderator_can_update_lesson(self):
        moderator = User.objects.create_user(
            email="test_moderator@example.com",
            password="test_password",
        )

        moderator_group, _ = Group.objects.get_or_create(name="Moderator")
        moderator_group.user_set.add(moderator)

        self.client.force_authenticate(moderator)

        url = reverse("lesson-detail", args=[self.lesson.id])

        data = {
            "title": "Test Moderator Update Lesson",
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.lesson.refresh_from_db()

        self.assertEqual(self.lesson.title, "Test Moderator Update Lesson")

    def test_lesson_create_invalid_video_url(self):
        url = reverse("lesson-list-create")

        data = {
            "course": self.course.id,
            "title": "Test Invalid Lesson",
            "description": "Lesson with invalid video url",
            "video_url": "https://example.com/video/123",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("video_url", response.data)
        self.assertFalse(Lesson.objects.filter(title="Test Invalid Lesson").exists())

    def test_unauthenticated_user_cannot_retrieve_lesson(self):
        self.client.force_authenticate(user=None)

        url = reverse("lesson-detail", args=[self.lesson.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SubscriptionTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="test_subscriber@example.com",
            password="test_password",
        )

        self.course = Course.objects.create(
            title="Test Subscription Course",
            description="Test subscription description",
            owner=self.user,
        )

        self.client.force_authenticate(user=self.user)

    def test_subscription_create(self):
        url = reverse("subscription")

        response = self.client.post(url, {"course_id": self.course.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

    def test_subscription_delete(self):
        Subscription.objects.create(
            user=self.user,
            course=self.course,
        )

        url = reverse("subscription")

        response = self.client.post(url, {"course_id": self.course.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

    def test_subscription_invalid_course(self):
        url = reverse("subscription")

        response = self.client.post(
            url,
            {"course_id": 99999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_unauthenticated_user_cannot_toggle_subscription(self):
        self.client.force_authenticate(user=None)

        url = reverse("subscription")

        response = self.client.post(url, {"course_id": self.course.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )


class CourseNotificationTaskTests(TestCase):
    def setUp(self):
        self.email_override = override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        )
        self.email_override.enable()

        self.addCleanup(self.email_override.disable)

    def test_email_sent_to_course_subscribers(self):
        User = get_user_model()

        owner = User.objects.create_user(
            email="owner@example.com",
            password="test_password",
        )

        subscriber_1 = User.objects.create_user(
            email="subscriber1@example.com",
            password="test_password",
        )

        subscriber_2 = User.objects.create_user(
            email="subscriber2@example.com",
            password="test_password",
        )

        course = Course.objects.create(
            title="Test Course",
            description="Test Course",
            owner=owner,
        )

        Subscription.objects.create(
            user=subscriber_1,
            course=course,
        )

        Subscription.objects.create(
            user=subscriber_2,
            course=course,
        )

        send_course_update_notification(course.id)

        self.assertEqual(len(mail.outbox), 1)

        self.assertCountEqual(
            mail.outbox[0].to,
            [
                "subscriber1@example.com",
                "subscriber2@example.com",
            ],
        )

    def test_no_email_sent_when_course_has_no_subscribers(self):
        User = get_user_model()

        owner = User.objects.create_user(
            email="owner@example.com",
            password="test_password",
        )

        course = Course.objects.create(
            title="Python Course",
            description="Learn Python programming",
            owner=owner,
        )

        result = send_course_update_notification(course.id)

        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(result, "No subscribers to notify.")


class CourseUpdateIntervalTests(TestCase):
    @patch("materials.views.send_course_update_notification.delay")
    def test_no_notification_within_four_hours(self, mock_delay):
        User = get_user_model()

        owner = User.objects.create(
            email="owner@example.com",
            password="test_password",
        )

        course = Course.objects.create(
            title="Python Course",
            description="Original description",
            owner=owner,
        )

        Course.objects.filter(pk=course.pk).update(
            updated_at=timezone.now() - timedelta(hours=2),
        )

        factory = APIRequestFactory()

        request = factory.patch(
            f"/courses/{course.pk}/",
            {"description": "Updated Description"},
            format="json",
        )

        force_authenticate(request, user=owner)

        view = CourseViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=course.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_delay.assert_not_called()

    @patch("materials.views.send_course_update_notification.delay")
    def test_notification_after_four_hours(self, mock_delay):
        User = get_user_model()

        owner = User.objects.create_user(
            email="owner@example.com",
            password="test_password",
        )

        course = Course.objects.create(
            title="Python Course",
            description="Learn Python programming",
            owner=owner,
        )

        Course.objects.filter(pk=course.pk).update(
            updated_at=timezone.now() - timedelta(hours=5),
        )

        factory = APIRequestFactory()

        request = factory.patch(
            f"courses/{course.pk}/",
            {"description": "Updated Description"},
            format="json",
        )

        force_authenticate(request, user=owner)

        view = CourseViewSet.as_view({"patch": "partial_update"})

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = view(request, pk=course.pk)

            mock_delay.assert_not_called()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(callbacks), 1)

        mock_delay.assert_called_once_with(course.pk)
