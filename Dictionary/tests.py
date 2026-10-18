from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from requests import RequestException

from Home.models import CustomUser


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class DictionarySearchSecurityTests(TestCase):
    def setUp(self):
        from Dictionary.views import get_english_dictionary_results

        get_english_dictionary_results.cache_clear()
        self.student = CustomUser.objects.create_user(username='dictionary-student', password='test-password-123')

    def tearDown(self):
        from Dictionary.views import get_english_dictionary_results

        get_english_dictionary_results.cache_clear()

    def test_search_requires_authentication(self):
        response = self.client.get(reverse('Search'), {'search': 'library'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.url.startswith(reverse('Search')))

    def test_search_rejects_empty_overlong_and_nonword_input_before_network_access(self):
        self.client.force_login(self.student)
        with patch('Dictionary.views.get') as get_request:
            for word in ('', 'x' * 65, 'http://example.invalid'):
                with self.subTest(word=word):
                    response = self.client.get(reverse('Search'), {'search': word})
                    self.assertEqual(response.status_code, 400)

        get_request.assert_not_called()

    def test_provider_failures_return_service_unavailable(self):
        self.client.force_login(self.student)
        with patch('Dictionary.views.get', side_effect=RequestException('synthetic timeout')) as get_request:
            response = self.client.get(reverse('Search'), {'search': 'library'})

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'dictionary service is temporarily unavailable', status_code=503)
        get_request.assert_called_once_with(
            'https://www.dictionary.com/browse/library',
            timeout=(3, 5),
        )

    def test_english_search_is_throttled_per_user_before_provider_access(self):
        self.client.force_login(self.student)
        with patch('Dictionary.views.get_english_dictionary_results', return_value=(['definition'], [], [])) as lookup:
            first_response = self.client.get(reverse('Search'), {'search': 'sample'})
            second_response = self.client.get(reverse('Search'), {'search': 'different'})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertContains(second_response, 'Please wait before searching again.', status_code=429)
        lookup.assert_called_once_with('sample')

    def test_global_search_leases_bound_concurrent_external_lookups(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from Dictionary.views import (
            acquire_global_search_lease,
            release_global_search_lease,
        )

        with TemporaryDirectory() as directory:
            with patch('Dictionary.views.SEARCH_LEASE_DIRECTORY', Path(directory)):
                first_lease = acquire_global_search_lease()
                second_lease = acquire_global_search_lease()
                third_lease = acquire_global_search_lease()

                self.assertIsNotNone(first_lease)
                self.assertIsNotNone(second_lease)
                self.assertIsNone(third_lease)

                release_global_search_lease(first_lease)
                replacement_lease = acquire_global_search_lease()
                self.assertIsNotNone(replacement_lease)

                release_global_search_lease(second_lease)
                release_global_search_lease(replacement_lease)

    def test_english_dictionary_results_are_cached_for_repeated_words(self):
        from Dictionary.views import get_english_dictionary_results

        with patch('Dictionary.views.BoundedDictionary') as dictionary_class:
            dictionary = dictionary_class.return_value
            dictionary.meanings.return_value = ['definition']
            dictionary.antonyms.return_value = []
            dictionary.synonyms.return_value = []

            first_result = get_english_dictionary_results('sample')
            second_result = get_english_dictionary_results('sample')

        self.assertEqual(first_result, (['definition'], [], []))
        self.assertIs(second_result, first_result)
        dictionary_class.assert_called_once_with('sample')
        dictionary.meanings.assert_called_once_with()
        dictionary.antonyms.assert_called_once_with()
        dictionary.synonyms.assert_called_once_with()

@override_settings(SECURE_SSL_REDIRECT=False)
class TagalogDictionarySearchSecurityTests(TestCase):
    def setUp(self):
        from Dictionary.views import get_tagalog_dictionary

        get_tagalog_dictionary.cache_clear()

    def tearDown(self):
        from Dictionary.views import get_tagalog_dictionary

        get_tagalog_dictionary.cache_clear()

    def test_anonymous_search_uses_cached_indexed_dictionary(self):
        from Dictionary.views import get_tagalog_dictionary

        entries = [
            {'word': 'bahay', 'definition': 'first definition'},
            {'word': 'bahay', 'definition': 'duplicate definition'},
        ]
        with patch('Dictionary.views.json.load', return_value=entries) as load_dictionary:
            first_response = self.client.get(reverse('Tagalog'), {'tagalog-search': 'bahay'})
            second_response = self.client.get(reverse('Tagalog'), {'tagalog-search': 'bahay'})

        self.assertContains(first_response, 'first definition')
        self.assertContains(second_response, 'first definition')
        load_dictionary.assert_called_once()
        self.assertEqual(get_tagalog_dictionary(), {'bahay': 'first definition'})

    def test_non_get_search_does_not_load_dictionary(self):
        with patch('Dictionary.views.json.load') as load_dictionary:
            response = self.client.post(reverse('Tagalog'), {'tagalog-search': 'bahay'})

        self.assertEqual(response.status_code, 405)
        load_dictionary.assert_not_called()
