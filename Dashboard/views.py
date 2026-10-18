from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalDeleteView
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from Home.models import StudentAttendance, GradeAndSection
from Home.forms import AttendanceForm, RegistrationForm
from .forms import AddGradeAndSectionForm, UpdateGradeAndSectionForm
import sweetify

# Create your views here.

@login_required(login_url='Choices')
def renderDashbaord(request):
    return render(request, "Dashboard/index.html")

@user_passes_test(lambda u: u.is_staff)
def systemUsers(request):
    data = list(StudentAttendance.objects.all().order_by('-id'))
    form = AttendanceForm()
    form2 = AddGradeAndSectionForm()
    form3 = RegistrationForm()
    
    if request.method == 'POST':
        form2 = AddGradeAndSectionForm(request.POST)
        if form2.is_valid():
            form2.save()
            sweetify.toast(request, 'New grade and section was successfully added. ', icon="success", timer=3000)
            return redirect('System')
        else:
            form = AddGradeAndSectionForm
            return render(request, 'System', {'form2':form2})
        
    context = {
        'data': data,
        'form': form,
        'form2': form2,
        'form3': form3
    }
    return render(request, 'Dashboard/system-users.html', context)

def editSystemUsers(request, pk):
    if request.user.is_authenticated == False:
        return redirect('Choices')
    if request.user.is_staff == False:
        return redirect('dashboard')
    
    data = StudentAttendance.objects.get(id=pk)
    form = AttendanceForm(instance=data)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=data)
        if form.is_valid():
            form.save()
            return redirect('System')
    
    context = {
        'form': form,
    }
    
    return render(request,'Dashboard/edit.html', context)

@user_passes_test(lambda user: user.is_staff, login_url='Choices')
@require_POST
def deleteSystemUsers(request, pk):
    data = StudentAttendance.objects.get(id=pk)
    data.delete()
    sweetify.toast(request, 'User succesfully deleted!', icon="success", timer=2500)
    return redirect('System')


@login_required(login_url='Choices')
def renderSections(request):
    data = GradeAndSection.objects.all()
    form = AddGradeAndSectionForm()
    
    if request.method == 'POST':
        if not request.user.is_staff:
            return HttpResponseForbidden()
        form = AddGradeAndSectionForm(request.POST)
        if form.is_valid():
            form.save()
            sweetify.toast(request, 'New grade and section was successfully added. ', icon="success", timer=3000)
            return redirect('Sections')
        else:
            form = AddGradeAndSectionForm
            return render(request, 'Sections', {'form':form})
        
    context = {
        'data': data,
        'form': form
    }
    
    return render(request, "Dashboard/sections.html", context)

@method_decorator(user_passes_test(lambda user: user.is_staff, login_url='Choices'), name='dispatch')
class updateSection(BSModalUpdateView):
    model = GradeAndSection
    template_name = 'Dashboard/update_sections.html'
    form_class = UpdateGradeAndSectionForm
    success_message = ''
    success_url = reverse_lazy('Sections')
    
@method_decorator(user_passes_test(lambda user: user.is_staff and user.is_superuser, login_url='Choices'), name='dispatch')
class deleteSection(BSModalDeleteView):
    model = GradeAndSection
    template_name = 'Dashboard/delete_sections.html'
    success_message = ''
    success_url = reverse_lazy('Sections')
    
    def get_context_data(self, **kwargs):       
        context = super().get_context_data(**kwargs)
        context['data'] = GradeAndSection.objects.get(pk=self.kwargs['pk'])
        return context
    
@require_POST
def logout_request(request):
    logout(request)
    sweetify.toast(request, 'You have succesfully logged out!', icon="success", timer=2500)
    return redirect("Choices")
