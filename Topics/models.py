from django.db import models
from Home.models import GradeAndSection
# Create your models here.


class TopicRecord(models.Model):
    topic = models.CharField(max_length=64, null=True)
    subject = models.CharField(max_length=64, null=True)
    grade_level = models.ForeignKey(GradeAndSection, on_delete=models.CASCADE, null=True, related_name='GradeAndSectionList')
    topic_file = models.FileField(upload_to="topic_files/")

    def __str__(self):
        return f"{self.topic}, {self.subject}, {self.topic_file}"