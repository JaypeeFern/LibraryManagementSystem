from django import forms
from  .models import StudentAttendance
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class RegistrationForm(UserCreationForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields["username"].widget.attrs.update({
            'class': 'form-control',
            'id': 'name',
            'placeholder': '#',
            'required': ''
        })

        self.fields["password1"].widget.attrs.update({
            'class': 'form-control',
            'id': 'name',
            'placeholder': '#',
            'required': ''
        })
        
        self.fields["password2"].widget.attrs.update({
            'class': 'form-control',
            'id': 'name',
            'placeholder': '#',
            'required': ''
        })
        
        self.fields["first_name"].widget.attrs.update({
            'class': 'form-control',
            'id': 'name',
            'placeholder': '#',
            'required': ''
        })
    
    class Meta:
        model = CustomUser
        fields=['first_name','username','password1','password2']

class LoginFormAuthentication(AuthenticationForm):
    
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        
        self.fields["username"].widget.attrs.update({
            'class': 'form-control',
            'id': 'username',
            'aria-describedby': 'usernameHelp',
            'required': '',
            'placeholder': 'None'
        })

        self.fields["password"].widget.attrs.update({
            'class': 'form-control',
            'id': 'password',
            'aria-describedby': 'passwordHelp',
            'required': '',
            'placeholder': 'None'
        })
        
class AttendanceForm(forms.ModelForm):
    
    class Meta:
        model = StudentAttendance
        fields = ('Student_Name', 'Grade_and_Section')
        widgets = {
            'Student_Name': forms.TextInput(attrs={'type': 'text', 'readonly': '', 'class': 'form-control-plaintext', 'placeholder': '#', 'value': '', 'id': 'floatingPlaintextInput'}),
            'Grade_and_Section': forms.Select(attrs={'class': 'form-select', 'id': "floatingSelect"}),
            
        }
