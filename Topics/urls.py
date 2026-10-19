from django.urls import path
from . import views


urlpatterns = [
    path('', views.renderTopics, name='Topics'),
    path('file/<int:pk>', views.topicFile, name='TopicFile'),
    path('update/<int:pk>', views.updateTopics.as_view(), name='UpdateTopic'),
    path('delete/<str:pk>', views.deleteTopics, name='DeleteTopics'),
    
]
