from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class GradeAndSection(models.Model):
    Grades = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f'{self. Grades}'

class CustomUser(AbstractUser):
    student_grade_level = models.ForeignKey(GradeAndSection, on_delete=models.CASCADE, null=True, blank=True)
    is_superuser = models.BooleanField(("superuser status"),default=False,help_text=("Designates that this user has all permissions without ""explicitly assigning them."))

class StudentAttendance(models.Model):
    Student_Name = models.CharField(max_length=64, null=True)
    Grade_and_Section = models.ForeignKey(GradeAndSection, on_delete=models.CASCADE, null=True)
    Attendance_Date = models.DateTimeField(auto_now_add=True)
    
    def get_grade_and_section(self):
        return self.Grade_and_Section.Grades
    
    def __str__(self):
        return f'{self.Student_Name}, {self.Grade_and_Section}, {self.Attendance_Date}'