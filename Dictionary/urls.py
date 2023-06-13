from django.urls import path
from . import views


urlpatterns = [
  path('english', views.renderEnglishDictionary, name='English-Dictionary'),
  path('tagalog', views.renderTagalogDictionary, name='Tagalog-Dictionary'),
  path('search', views.searchView, name='Search'),
  path('search/tagalog', views.tagalogSearchView, name='Tagalog')
]