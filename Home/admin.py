from django.contrib import admin
from .models import *

# Register your models here.

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id','username','first_name','last_name','email','is_staff','is_active','is_superuser')
admin.site.register(CustomUser, CustomUserAdmin)

class GradeAndSectionListAdmin(admin.ModelAdmin):
    list_display = ('id','Grades')
    ordering = ('id',)
    search_fields = ('id','Grades')
admin.site.register(GradeAndSection,GradeAndSectionListAdmin)

class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('id','Student_Name', 'Grade_and_Section','Attendance_Date')
    ordering = ('id',)
    search_fields = ('id','Student_Name')
admin.site.register(StudentAttendance,StudentAttendanceAdmin)