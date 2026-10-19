from django.conf import settings
from django.db import models


class DictionarySearchThrottle(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    last_search_at = models.DateTimeField()
