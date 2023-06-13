from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="Home"),
    path('choices', views.choices, name='Choices'),
    path('login/student', views.loginStudent, name='Student'),
    path('login/student/attendance', views.studentAttendance, name='Attendance'),
    path('login/teacher', views.loginTeacher, name='Teacher'),
    path('choices/register', views.register, name='Register')
]