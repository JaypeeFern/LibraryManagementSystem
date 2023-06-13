from django.urls import path
from . import views


urlpatterns = [
    path('', views.renderStories, name='Stories'),
    path('/delete/<str:pk>', views.deleteStories, name='/DeleteStories/'),
]