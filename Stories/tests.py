from pathlib import Path
from tempfile import TemporaryDirectory

from django.http import FileResponse
from django.test import Client, TestCase, override_settings
from django.test import RequestFactory
from django.urls import reverse

from Home.models import CustomUser
from .models import StoriesRecord
from .middleware import RangesMiddleware


TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class StoryAuthorizationTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username='teacher',
            password='test-password-123',
            is_staff=True,
        )
        self.student = CustomUser.objects.create_user(
            username='student',
            password='test-password-123',
        )
        self.story = StoriesRecord.objects.create(
            story_name='Lesson',
            story_vid='lesson.mp4',
        )

    def test_public_read_access_is_preserved(self):
        response = self.client.get(reverse('Stories'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lesson')

    def test_anonymous_user_cannot_upload_or_delete_stories(self):
        upload_response = self.client.post(reverse('Stories'), {
            'story_name': 'Anonymous lesson',
            'story_description': 'Test',
        })
        delete_response = self.client.post(reverse('DeleteStories', args=[self.story.pk]))

        self.assertEqual(upload_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(StoriesRecord.objects.filter(story_name='Anonymous lesson').exists())
        self.assertTrue(StoriesRecord.objects.filter(pk=self.story.pk).exists())

    def test_non_staff_cannot_create_stories(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse('Stories'), {
            'story_name': 'Unauthorized lesson',
            'story_description': 'Test',
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(StoriesRecord.objects.filter(story_name='Unauthorized lesson').exists())

    def test_staff_can_create_stories(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Stories'), {
            'story_name': 'Authorized lesson',
            'story_description': 'Test',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(StoriesRecord.objects.filter(story_name='Authorized lesson').exists())

    def test_story_delete_is_staff_only_and_post_only(self):
        self.client.force_login(self.staff)

        get_response = self.client.get(reverse('DeleteStories', args=[self.story.pk]))
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(StoriesRecord.objects.filter(pk=self.story.pk).exists())

        post_response = self.client.post(reverse('DeleteStories', args=[self.story.pk]))
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(StoriesRecord.objects.filter(pk=self.story.pk).exists())

    def test_story_delete_form_includes_csrf_token(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('Stories'))

        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_delete_rejects_missing_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)

        csrf_client.get(reverse('Stories'))
        response = csrf_client.post(reverse('DeleteStories', args=[self.story.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(StoriesRecord.objects.filter(pk=self.story.pk).exists())


class RangeMiddlewareTests(TestCase):
    def process_file_range(self, contents, range_header):
        temp_directory = TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / 'video.bin'
        file_path.write_bytes(contents)
        file_stream = file_path.open('rb')
        response = FileResponse(file_stream)
        request = RequestFactory().get('/media/video.bin', HTTP_RANGE=range_header)

        return RangesMiddleware(lambda request: None).process_response(request, response)

    def test_malformed_and_unsatisfiable_single_ranges_return_416(self):
        for range_header in ('bytes=bad-range', 'bytes=9-12', 'bytes=4-2'):
            with self.subTest(range_header=range_header):
                response = self.process_file_range(b'1234', range_header)

                self.assertEqual(response.status_code, 416)
                self.assertEqual(response['Content-Range'], 'bytes */4')

    def test_zero_byte_file_range_returns_416(self):
        response = self.process_file_range(b'', 'bytes=0-')

        self.assertEqual(response.status_code, 416)
        self.assertEqual(response['Content-Range'], 'bytes */0')

    def test_suffix_range_returns_requested_tail(self):
        response = self.process_file_range(b'123456', 'bytes=-3')

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Range'], 'bytes 3-5/6')
        self.assertEqual(b''.join(response.streaming_content), b'456')

    def test_valid_open_ended_range_preserves_partial_content(self):
        response = self.process_file_range(b'123456', 'bytes=2-')

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Range'], 'bytes 2-5/6')
        self.assertEqual(b''.join(response.streaming_content), b'3456')
