from django.contrib import admin
from .models import StoriesRecord
# Register your models here.


class StoriesAdmin(admin.ModelAdmin):
    list_display = ('id','reference_number', 'story_name','story_description', 'story_vid', 'story_thumbnail', 'date_uploadeded')
    ordering = ('id',)
    search_fields = ('id','story_name')
admin.site.register(StoriesRecord,StoriesAdmin)