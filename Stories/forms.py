from django import forms
from .models import StoriesRecord

class AddStoryForm(forms.ModelForm):
    
    class Meta:
        model = StoriesRecord
        fields = ('story_name', 'story_description', 'story_vid')
        widgets = {
            'story_name': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'story', 'placeholder': '#'}),
            'story_description': forms.Textarea(attrs={'class': 'form-control', 'id': 'description', 'placeholder': '#'}),
            'story_vid': forms.FileInput(attrs={'class': 'form-control', 'type': 'file', 'id': 'video'})
        }
