from django.urls import path
from . import views

urlpatterns = [
    
    path("home", views.renderDashbaord, name="dashboard"),
    path('home/system-users', views.systemUsers, name='System'),
    path('home/system-users/sections', views.renderSections, name='Sections'),
    path('home/system-users/sections/update/<int:pk>', views.updateSection.as_view(), name='UpdateSection'),
    path('home/system-users/sections/delete/<int:pk>', views.deleteSection.as_view(), name='DeleteSection'),
    path('home/system-users/edit/<str:pk>', views.editSystemUsers, name='Edit'),
    path('home/system-users/delete/<str:pk>', views.deleteSystemUsers, name='Delete'),
    path('home/logout', views.logout_request, name='Logout')
    
]