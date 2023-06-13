from django.db import models
import secrets
import string
# Create your models here.

def randomGenerator():
    alphabet = string.ascii_letters
    random = ''.join(secrets.choice(alphabet) for i in range(10))
    return random

def defaultDescription():
    return 'Description not available.'

class StoriesRecord(models.Model):
    reference_number = models.CharField(max_length=10, editable=False, default=randomGenerator)
    story_name = models.CharField(max_length=64, null=True)
    story_description = models.TextField(max_length=300, null=True, blank=True, default=defaultDescription)
    story_vid = models.FileField(upload_to="stories_files/video", blank=True)
    story_thumbnail = models.ImageField(upload_to="stories_files/thumb", blank=True)
    date_uploadeded = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference_number}, {self.story_name}, {self.story_description}, {self.story_vid}, {self.story_thumbnail}, {self.date_uploadeded}"
