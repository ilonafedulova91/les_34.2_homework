from django.db import models

from users.models import User


class Course(models.Model):
    title = models.CharField(max_length=200)
    preview = models.ImageField(upload_to="courses/previews/", blank=True, null=True)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")

    title = models.CharField(max_length=200)
    preview = models.ImageField(upload_to="lessons/previews/", blank=True, null=True)
    description = models.TextField()
    video_url = models.URLField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lessons")

    def __str__(self):
        return self.title


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subscriptions"
    )

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user}: {self.course}"
