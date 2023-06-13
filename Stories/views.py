from django.shortcuts import render, redirect
from .models import StoriesRecord
from .forms import AddStoryForm
import sweetify

# Create your views here.

def renderStories(request):
    
    form = AddStoryForm()
    if request.method == 'POST':
        form = AddStoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            sweetify.toast(request, 'New story was successfully added. ', icon="success", timer=3000)
            return redirect('Stories')
        else:
            form = AddStoryForm
            return render(request, 'Stories', {'form':form})
    
    context = {
        "data": StoriesRecord.objects.all(),
        'form': form
    }
    
    return render(request, 'Stories/index.html', context)

def deleteStories(request, pk):
    data = StoriesRecord.objects.get(id=pk)
    data.delete()
    sweetify.toast(request, 'Story succesfully deleted!', icon="success", timer=2500)
    return redirect('Stories')