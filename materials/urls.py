from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (CourseViewSet, LessonListCreateAPIView,
                    LessonRetrieveUpdateDestroyAPIView, SubscriptionAPIView)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")


urlpatterns = [
    path("lessons/", LessonListCreateAPIView.as_view(), name="lesson-list-create"),
    path(
        "lessons/<int:pk>/",
        LessonRetrieveUpdateDestroyAPIView.as_view(),
        name="lesson-detail",
    ),
    path("subscriptions/", SubscriptionAPIView.as_view(), name="subscription"),
]

urlpatterns += router.urls
