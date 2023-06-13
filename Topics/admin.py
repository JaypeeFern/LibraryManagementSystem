from django.contrib import admin
from .models import TopicRecord

# Register your models here.

class TopicAdmin(admin.ModelAdmin):
    list_display = ('id','topic','subject','grade_level','topic_file')
    ordering = ('id','topic')
    search_fields = ('id','topic')
admin.site.register(TopicRecord,TopicAdmin)