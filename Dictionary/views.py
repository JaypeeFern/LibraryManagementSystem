from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from bs4 import BeautifulSoup
from pydictionary import Dictionary
from requests import get, RequestException
import json
import sweetify

# Create your views here.

def renderEnglishDictionary(request):
    return render(request, 'Dictionary/index.html')

def renderTagalogDictionary(request):
    return render(request, 'Dictionary/tagalog.html')

REQUEST_TIMEOUT_SECONDS = (3, 5)
MAX_SEARCH_LENGTH = 64


class BoundedDictionary(Dictionary):
    def soup_result(self, url):
        self.url = url
        response = get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        self.response = response.content
        self.soup = BeautifulSoup(self.response, 'lxml')
        return self.soup


@login_required(login_url='Choices')
@require_GET
def searchView(request):

    # capturing the word from the form via the name search
    word = request.GET.get('search', '').strip()
    if not word or len(word) > MAX_SEARCH_LENGTH or any(not (char.isalpha() or char.isdigit() or char in " '-") for char in word):
        return HttpResponseBadRequest('Enter a word or phrase of up to 64 letters.')

    try:
        dictionary = BoundedDictionary(word)
        meanings = dictionary.meanings()
        antonym_results = dictionary.antonyms()
        synonym_results = dictionary.synonyms()
    except RequestException:
        return HttpResponse('The dictionary service is temporarily unavailable. Please try again.', status=503)
    
    antonymsQuery = antonym_results[:5]
    synonymsQuery = synonym_results[:5]
   
    # bundling all the variables in the context  
    context = {
            'word': word,
            'meanings':meanings,
            'synonyms':antonymsQuery,
            'antonoyms':synonymsQuery
        }
    
    return render(request, 'Dictionary/index.html', context)

def tagalogSearchView(request):
    
    url = (
    "Dictionary/static/Dictionary/json"
    )
    
    data = f"{url}/tagalog_dictionary.json"
    opt = open(data)
    data1 = json.load(opt)
    
    for i in data1:
        word = request.GET.get('tagalog-search')
        if i['word'] == f'{word}':
            tword = i['word']
            definition = i['definition']
            
            context = {
            'tword': tword,
            'definition': definition
            }

            return render(request, 'Dictionary/tagalog.html', context)
        
    error = sweetify.toast(request, 'Word not found.', icon="error", timer=3000)
    return render(request, 'Dictionary/tagalog.html', {'error':error})
