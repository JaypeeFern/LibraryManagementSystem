from django.shortcuts import render, redirect
from .forms import RegistrationForm, LoginFormAuthentication, AttendanceForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import CustomUser, GradeAndSection
import sweetify


# Create your views here.

def index(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/home')
    return render(request, 'Home/index.html')

def choices(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/home')
    
    form2 = RegistrationForm(request.POST)
    form = LoginFormAuthentication(request, data=request.POST)
    
    return render(request, "Home/choices.html", {
        "form": form,
        'form2': form2
        
        })
    
@login_required(login_url='Choices')
def studentAttendance(request):
    assigned_grade = request.user.student_grade_level
    form = AttendanceForm()
    if assigned_grade is None:
        return render(request, 'Home/attendance.html', {
            'form': form,
            'attendance_error': 'Your grade and section has not been assigned. Please contact a staff member.',
        }, status=403)

    form.fields['Grade_and_Section'].queryset = GradeAndSection.objects.filter(pk=assigned_grade.pk)
    form.initial['Grade_and_Section'] = assigned_grade
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        form.fields['Grade_and_Section'].queryset = GradeAndSection.objects.filter(pk=assigned_grade.pk)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.Student_Name = request.user.get_full_name() or request.user.get_username()
            attendance.Grade_and_Section = assigned_grade
            attendance.save()
            sweetify.toast(request, 'Attendance succesfully recorded!', icon="success", timer=3000)
            return redirect('/dashboard/home')
        return render(request, 'Home/attendance.html', {'form': form})
    
    return render(request, 'Home/attendance.html', {
        'form': form,
    })

def loginStudent(request):
    form = LoginFormAuthentication(request, data=request.POST)
    form2 = RegistrationForm()
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        sweetify.success(request, 'Successfully logged in!', button='Ok', timer=1500)
        return redirect("Attendance")
    else:
        if request.method == "POST":
            # AuthenticationForm already tried the configured authentication backend.
            error = sweetify.toast(request, 'Account does not exist!', icon="error", timer=3000)
            return render(request, "Home/choices.html",{"form": form, 'form2': form2, "error": error })
    return render(request, "Home/choices.html", {"form": form, 'form2': form2})
    
def loginTeacher(request):
    form = LoginFormAuthentication(request, data=request.POST)
    form2 = RegistrationForm()
    if form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            sweetify.error(request, 'Account is not authorized!', button='Ok', timer=1500)
            return redirect("/choices")
        login(request, user)
        sweetify.success(request, 'Successfully logged in!', button='Ok', timer=1500)
        return redirect("/dashboard/home")
    else:
        if request.method == "POST":
            # AuthenticationForm already tried the configured authentication backend.
            error = sweetify.toast(request, 'Account does not exist!', icon="error", timer=3000)
            return render(request, "Home/choices.html",{"form": form, 'form2': form2, "error": error })
    return render(request, "Home/choices.html", {"form": form, 'form2': form2})

@user_passes_test(lambda user: user.is_staff, login_url='Choices')
def register(request):
    form = LoginFormAuthentication(request, data=request.POST)
    form2 = RegistrationForm()
    if request.method == "POST":
        form2 = RegistrationForm(request.POST)
        username = request.POST.get("username")
        if CustomUser.objects.filter(username=username).exists():
            sweetify.toast(request, 'Username already exists! Please try again', icon="error", timer=3000)
            return redirect('System')
            
        if form2.is_valid():
            user = form2.save()
            # login(request, user)
            sweetify.toast(request, 'You have succesfully registered!', icon="success", timer=3000)
            return redirect("System")
        else:
            password1 = form2.cleaned_data.get('password1')
            password2 = form2.cleaned_data.get('password2')
            if password1 != password2:
                sweetify.toast(request, 'Password do not match', icon="error", timer=3000)
                # return render(request, 'Dashboard/system-users.html', {'form': form, 'form2': form2})
                return redirect('System')
            # return render(request, 'Dashboard/system-users.html', {'form': form, 'form2': form2})
            return redirect('System')
