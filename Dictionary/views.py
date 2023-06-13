from django.shortcuts import render, redirect
from pydictionary import Dictionary
from wordhoard import Antonyms, Synonyms
import json, sweetify

# Create your views here.

def renderEnglishDictionary(request):
    return render(request, 'Dictionary/index.html')

def renderTagalogDictionary(request):
    return render(request, 'Dictionary/tagalog.html')

def searchView(request):

    # capturing the word from the form via the name search
    word = request.GET.get('search')
    # creating a dictionary object
    dictionary = Dictionary(word)
    # passing a word to the dictionary object
    meanings = dictionary.meanings()
    # getting a synonym and antonym  
    antonyms = Antonyms(search_string=word, output_format='list')
    antonym_results = antonyms.find_antonyms()
    
    synonyms = Synonyms(search_string=word, output_format='list')
    synonym_results = synonyms.find_synonyms()
    
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
        