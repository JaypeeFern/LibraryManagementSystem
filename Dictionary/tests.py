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
        self.student = CustomUser.objects.create_user(username='dictionary-student', password='test-password-123')

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
