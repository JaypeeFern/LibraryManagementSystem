from django.shortcuts import render, redirect
from .forms import RegistrationForm, LoginFormAuthentication, AttendanceForm
from django.contrib.auth import authenticate, login, logout 
from .models import CustomUser
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
    
def studentAttendance(request):
    form = AttendanceForm()
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            get_user_id = request.POST.get('user')
            data = CustomUser.objects.filter(id=get_user_id)
            converyQuery = data.values()
            converyQuery.update(student_grade_level=request.POST.get('Grade_and_Section'))
            form.save()
            sweetify.toast(request, 'Attendance succesfully recorded!', icon="success", timer=3000)
            return redirect('/dashboard/home')
        else:
            form = AttendanceForm
            return render(request, 'Home/attendance.html', {'form':form})
    
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
            # get data from input fields username & password (Default fieldtext names django)
            username = request.POST.get("username")
            password = request.POST.get("password")
            # Authenticate user using django authenticate function
            user = authenticate(request, username=username, password=password)
            # If user does not exist (None) in database execute return function and display error message
            if user is None:
                error = sweetify.toast(request, 'Account does not exist!', icon="error", timer=3000)
                return render(request, "Home/choices.html",{"form": form, 'form2': form2, "error": error })
    
def loginTeacher(request):
    form = LoginFormAuthentication(request, data=request.POST)
    form2 = RegistrationForm()
    if form.is_valid():
        username = request.POST['username']
        password = request.POST['password']
        account = authenticate(request, username=username, password=password)
        if account is not None and account.is_staff == False:
            sweetify.error(request, 'Account is not authorized!', button='Ok', timer=1500)
            return redirect("/choices")
        user = form.get_user()
        login(request, user)
        sweetify.success(request, 'Successfully logged in!', button='Ok', timer=1500)
        return redirect("/dashboard/home")
    else:
        if request.method == "POST":
            # get data from input fields username & password (Default fieldtext names django)
            username = request.POST.get("username")
            password = request.POST.get("password")
            # Authenticate user using django authenticate function
            user = authenticate(request, username=username, password=password)
            # If user does not exist (None) in database execute return function and display error message
            if user is None:
                error = sweetify.toast(request, 'Account does not exist!', icon="error", timer=3000)
                return render(request, "Home/choices.html",{"form": form, 'form2': form2, "error": error })

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
            
            