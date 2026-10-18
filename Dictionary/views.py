from datetime import timedelta
from functools import lru_cache
import os
from pathlib import Path
import tempfile

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from bs4 import BeautifulSoup
from pydictionary import Dictionary
from requests import get, RequestException
import json
import sweetify

from .models import DictionarySearchThrottle

# Create your views here.

def renderEnglishDictionary(request):
    return render(request, 'Dictionary/index.html')

def renderTagalogDictionary(request):
    return render(request, 'Dictionary/tagalog.html')

REQUEST_TIMEOUT_SECONDS = (3, 5)
MAX_SEARCH_LENGTH = 64
SEARCH_COOLDOWN = timedelta(seconds=2)
# Keep one of Gunicorn's three synchronous workers free for other requests.
MAX_CONCURRENT_DICTIONARY_SEARCHES = 2
SEARCH_LEASE_DIRECTORY = Path(tempfile.gettempdir()) / 'library-dictionary-search-leases'


class BoundedDictionary(Dictionary):
    def soup_result(self, url):
        self.url = url
        response = get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        self.response = response.content
        self.soup = BeautifulSoup(self.response, 'lxml')
        return self.soup


def acquire_search_slot(user_id):
    now = timezone.now()
    cooldown_ended_at = now - SEARCH_COOLDOWN

    with transaction.atomic():
        updated = DictionarySearchThrottle.objects.filter(
            user_id=user_id,
            last_search_at__lte=cooldown_ended_at,
        ).update(last_search_at=now)
        if updated:
            return True

        try:
            with transaction.atomic():
                DictionarySearchThrottle.objects.create(user_id=user_id, last_search_at=now)
        except IntegrityError:
            return False

    return True


def acquire_global_search_lease():
    SEARCH_LEASE_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)

    for slot in range(1, MAX_CONCURRENT_DICTIONARY_SEARCHES + 1):
        lease_file = (SEARCH_LEASE_DIRECTORY / f'{slot}.lock').open('a+b')
        try:
            if os.name == 'nt':
                lease_file.seek(0)
                if not lease_file.read(1):
                    lease_file.write(b'\0')
                    lease_file.flush()
                lease_file.seek(0)
                msvcrt.locking(lease_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lease_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lease_file
        except OSError:
            lease_file.close()

    return None


def release_global_search_lease(lease):
    try:
        if os.name == 'nt':
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lease.fileno(), fcntl.LOCK_UN)
    finally:
        lease.close()


@lru_cache(maxsize=256)
def get_english_dictionary_results(word):
    dictionary = BoundedDictionary(word)
    meanings = dictionary.meanings()
    antonyms = dictionary.antonyms()[:5]
    synonyms = dictionary.synonyms()[:5]
    return meanings, antonyms, synonyms


@lru_cache(maxsize=1)
def get_tagalog_dictionary():
    dictionary_path = Path(__file__).resolve().parent / 'static' / 'Dictionary' / 'json' / 'tagalog_dictionary.json'
    with dictionary_path.open(encoding='utf-8') as dictionary_file:
        entries = json.load(dictionary_file)

    word_index = {}
    for entry in entries:
        word_index.setdefault(entry['word'], entry['definition'])
    return word_index


@login_required(login_url='Choices')
@require_GET
def searchView(request):

    # capturing the word from the form via the name search
    word = request.GET.get('search', '').strip()
    if not word or len(word) > MAX_SEARCH_LENGTH or any(not (char.isalpha() or char.isdigit() or char in " '-") for char in word):
        return HttpResponseBadRequest('Enter a word or phrase of up to 64 letters.')

    if not acquire_search_slot(request.user.pk):
        return HttpResponse('Please wait before searching again.', status=429)

    search_lease = acquire_global_search_lease()
    if search_lease is None:
        return HttpResponse('Dictionary searches are busy. Please try again shortly.', status=429)

    try:
        meanings, antonym_results, synonym_results = get_english_dictionary_results(word)
    except RequestException:
        return HttpResponse('The dictionary service is temporarily unavailable. Please try again.', status=503)
    finally:
        release_global_search_lease(search_lease)
    
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

@require_GET
def tagalogSearchView(request):
    word = request.GET.get('tagalog-search', '')
    definition = get_tagalog_dictionary().get(word)
    if definition is not None:
        context = {
            'tword': word,
            'definition': definition,
        }
        return render(request, 'Dictionary/tagalog.html', context)

    error = sweetify.toast(request, 'Word not found.', icon="error", timer=3000)
    return render(request, 'Dictionary/tagalog.html', {'error':error})
