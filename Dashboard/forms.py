from django import forms
from Home.models import GradeAndSection
from bootstrap_modal_forms.forms import BSModalModelForm

class AddGradeAndSectionForm(forms.ModelForm):
    
    class Meta:
        model = GradeAndSection
        fields = ('Grades',)
        widgets = {
            'Grades': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'topic', 'placeholder': '#'}),
        }
        
class UpdateGradeAndSectionForm(BSModalModelForm):
    
    class Meta:
        model = GradeAndSection
        fields = ('Grades',)
        widgets = {
            'Grades': forms.TextInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'topic', 'placeholder': '#'}),
        }
