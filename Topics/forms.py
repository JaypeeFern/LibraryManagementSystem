from django import forms
from .models import TopicRecord
from bootstrap_modal_forms.forms import BSModalModelForm

class AddTopicForm(forms.ModelForm):
    
    class Meta:
        model = TopicRecord
        fields = ('topic', 'subject', 'grade_level', 'topic_file')
        widgets = {
            'topic': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'topic', 'placeholder': '#'}),
            'subject': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'subject', 'placeholder': '#'}),
            'grade_level': forms.Select(attrs={'class': 'form-select', 'id': 'grade_level'}),
            'topic_file': forms.FileInput(attrs={'class': 'form-control', 'type': 'file', 'id': 'formFile'})
        }
        
class UpdateTopicForm(BSModalModelForm):
    
    class Meta:
        model = TopicRecord
        fields = ('topic', 'subject', 'topic_file')
        widgets = {
            'topic': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'topic', 'placeholder': '#'}),
            'subject': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'subject', 'placeholder': '#'}),
            'topic_file': forms.FileInput(attrs={'class': 'form-control', 'type': 'file', 'id': 'formFile'})
        }