from ast import Add
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import AddTopicForm, UpdateTopicForm
from .models import TopicRecord
from bootstrap_modal_forms.generic import BSModalUpdateView
from django.db.models import Q
import sweetify

# Create your views here.


def renderTopics(request):
    form = AddTopicForm()
    if request.method == 'POST':
        form = AddTopicForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            sweetify.toast(request, 'New topic was successfully added. ', icon="success", timer=3000)
            return redirect('/dashboard/topics')
        else:
            form = AddTopicForm
            return render(request, 'Topics.index.html', {'form':form})
    
    if request.user.is_staff | request.user.is_superuser:
        return render(request, 'Topics/index.html', {
            'form': form,
            'data': TopicRecord.objects.all()
        })
    else:
        return render(request, 'Topics/index.html', {
            'form': form,
            'data': TopicRecord.objects.filter(Q(grade_level=request.user.student_grade_level))
        })
    
class updateTopics(BSModalUpdateView):
    model = TopicRecord
    template_name = 'Topics/update_topics.html'
    form_class = UpdateTopicForm
    success_message = ''
    success_url = reverse_lazy('Topics')

def deleteTopics(request, pk):
    data = TopicRecord.objects.get(id=pk)
    data.delete()
    sweetify.toast(request, 'Topic succesfully deleted!', icon="success", timer=2500)
    return redirect('Topics')