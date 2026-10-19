from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import StopUpload
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse
from django.test import Client, TestCase, override_settings
from django.test import RequestFactory
from django.urls import reverse

from PIL import Image

from backend.uploads import (
    MAX_STORY_THUMBNAIL_BYTES,
    MAX_STORY_VIDEO_BYTES,
    UploadLimitHandler,
    validate_story_thumbnail,
    validate_story_video,
)
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
            'story_vid': SimpleUploadedFile('lesson.mp4', b'\x00\x00\x00\x18ftypmp42'),
        })

        self.assertEqual(response.status_code, 302)
        story = StoriesRecord.objects.get(story_name='Authorized lesson')
        self.assertEqual(story.story_vid.name.rsplit('/', 1)[-1], 'lesson.mp4')

    def test_story_upload_accepts_mp4_and_rejects_mismatched_or_oversized_files(self):
        valid_mp4 = SimpleUploadedFile('lesson.mp4', b'\x00\x00\x00\x18ftypmp42')
        validate_story_video(valid_mp4)

        with self.assertRaises(ValidationError):
            validate_story_video(SimpleUploadedFile('lesson.mp4', b'<html>not video</html>'))
        with self.assertRaises(ValidationError):
            validate_story_video(SimpleUploadedFile('lesson.avi', b'\x00\x00\x00\x18ftypmp42'))

        oversized_video = SimpleUploadedFile('lesson.mp4', b'\x00\x00\x00\x18ftypmp42')
        oversized_video.size = MAX_STORY_VIDEO_BYTES + 1
        with self.assertRaises(ValidationError):
            validate_story_video(oversized_video)

        oversized_thumbnail = SimpleUploadedFile('poster.png', b'\x89PNG\r\n\x1a\n')
        oversized_thumbnail.size = MAX_STORY_THUMBNAIL_BYTES + 1
        with self.assertRaises(ValidationError):
            validate_story_thumbnail(oversized_thumbnail)

        for image_format, filename in (('JPEG', 'poster.jpg'), ('PNG', 'poster.png')):
            with self.subTest(filename=filename):
                image_bytes = BytesIO()
                Image.new('RGB', (1, 1), color='red').save(image_bytes, format=image_format)
                validate_story_thumbnail(SimpleUploadedFile(filename, image_bytes.getvalue()))

        with self.assertRaises(ValidationError):
            validate_story_thumbnail(SimpleUploadedFile('poster.png', b'<html>not an image</html>'))

    def test_staff_upload_validation_error_renders_story_form_again(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Stories'), {
            'story_name': 'Invalid lesson',
            'story_description': 'Test',
            'story_vid': SimpleUploadedFile('lesson.mp4', b'<html>not video</html>'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The file content is not an MP4 video')
        self.assertFalse(StoriesRecord.objects.filter(story_name='Invalid lesson').exists())

    def test_story_admin_rejects_invalid_video_content(self):
        administrator = CustomUser.objects.create_superuser(
            username='administrator',
            password='test-password-123',
        )
        self.client.force_login(administrator)

        response = self.client.post(reverse('admin:Stories_storiesrecord_add'), {
            'story_name': 'Admin upload',
            'story_description': 'Test',
            'story_vid': SimpleUploadedFile('lesson.mp4', b'<html>not video</html>'),
            'story_thumbnail': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The file content is not an MP4 video')
        self.assertFalse(StoriesRecord.objects.filter(story_name='Admin upload').exists())

    def test_upload_handler_rejects_file_while_streaming_before_other_handlers(self):
        request = SimpleNamespace(upload_limit_exceeded=False)
        handler = UploadLimitHandler(request)
        handler.new_file('story_vid', 'lesson.mp4', 'video/mp4', None, None, None)

        with self.assertRaises(StopUpload):
            handler.receive_data_chunk(b'x', MAX_STORY_VIDEO_BYTES)

        self.assertTrue(request.upload_limit_exceeded)

    def test_upload_limit_middleware_returns_413_for_oversized_request(self):
        self.client.force_login(self.staff)

        with patch('backend.uploads.UPLOAD_LIMITS_BY_FIELD', {'story_vid': 4}), patch(
            'backend.uploads.MAX_TOTAL_UPLOAD_BYTES', 4
        ):
            response = self.client.post(reverse('Stories'), {
                'story_name': 'Oversized lesson',
                'story_description': 'Test',
                'story_vid': SimpleUploadedFile('lesson.mp4', b'12345'),
            })

        self.assertEqual(
            response.status_code,
            413,
            f"location={response.get('Location')}, limit_exceeded={getattr(response.wsgi_request, 'upload_limit_exceeded', None)}",
        )
        self.assertFalse(StoriesRecord.objects.filter(story_name='Oversized lesson').exists())

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
