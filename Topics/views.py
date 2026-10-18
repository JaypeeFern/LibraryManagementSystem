from ast import Add
import mimetypes

from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.urls import reverse_lazy
from .forms import AddTopicForm, UpdateTopicForm
from .models import TopicRecord
from bootstrap_modal_forms.generic import BSModalUpdateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
import sweetify

# Create your views here.


@login_required(login_url='Choices')
def renderTopics(request):
    form = AddTopicForm()
    if request.method == 'POST':
        if not request.user.is_staff:
            return HttpResponseForbidden()
        form = AddTopicForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            sweetify.toast(request, 'New topic was successfully added. ', icon="success", timer=3000)
            return redirect('/dashboard/topics')
        return render(request, 'Topics/index.html', {
            'form': form,
            'data': TopicRecord.objects.all(),
        })
    
    if request.user.is_staff or request.user.is_superuser:
        return render(request, 'Topics/index.html', {
            'form': form,
            'data': TopicRecord.objects.all()
        })
    else:
        assigned_grade = request.user.student_grade_level
        topics = TopicRecord.objects.none()
        if assigned_grade is not None:
            topics = TopicRecord.objects.filter(grade_level=assigned_grade)
        return render(request, 'Topics/index.html', {
            'form': form,
            'data': topics
        })


@login_required(login_url='Choices')
def topicFile(request, pk):
    topic = get_object_or_404(TopicRecord, pk=pk)
    return _serve_topic_file(request, topic)


@login_required(login_url='Choices')
def topicFileByPath(request, file_path):
    topic = get_object_or_404(TopicRecord, topic_file=f'topic_files/{file_path}')
    return _serve_topic_file(request, topic)


def _serve_topic_file(request, topic):
    if not (request.user.is_staff or request.user.is_superuser):
        assigned_grade = request.user.student_grade_level
        if assigned_grade is None or topic.grade_level_id != assigned_grade.pk:
            raise Http404

    try:
        topic_file = topic.topic_file.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404

    content_type = mimetypes.guess_type(topic.topic_file.name)[0] or 'application/octet-stream'
    response = FileResponse(
        topic_file,
        as_attachment=request.GET.get('download') == '1',
        filename=topic.topic_file.name.rsplit('/', 1)[-1],
        content_type=content_type,
    )
    response['Cache-Control'] = 'private, no-store'
    return response
    
@method_decorator(user_passes_test(lambda user: user.is_staff, login_url='Choices'), name='dispatch')
class updateTopics(BSModalUpdateView):
    model = TopicRecord
    template_name = 'Topics/update_topics.html'
    form_class = UpdateTopicForm
    success_message = ''
    success_url = reverse_lazy('Topics')

@user_passes_test(lambda user: user.is_staff, login_url='Choices')
@require_POST
def deleteTopics(request, pk):
    data = TopicRecord.objects.get(id=pk)
    data.delete()
    sweetify.toast(request, 'Topic succesfully deleted!', icon="success", timer=2500)
    return redirect('Topics')
