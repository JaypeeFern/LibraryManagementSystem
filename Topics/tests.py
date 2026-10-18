from tempfile import TemporaryDirectory
from io import BytesIO
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from Home.models import CustomUser, GradeAndSection
from backend.uploads import MAX_TOPIC_FILE_BYTES, validate_topic_file
from .forms import AddTopicForm
from .models import TopicRecord


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
class TopicAuthorizationTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.grade = GradeAndSection.objects.create(Grades='Grade 6')
        self.staff = CustomUser.objects.create_user(
            username='teacher',
            password='test-password-123',
            is_staff=True,
        )
        self.student = CustomUser.objects.create_user(
            username='student',
            password='test-password-123',
            student_grade_level=self.grade,
        )
        self.topic = TopicRecord.objects.create(
            topic='Reading',
            subject='English',
            grade_level=self.grade,
            topic_file='fixture.pdf',
        )
        self.topic.topic_file.save('reading.pdf', ContentFile(b'%PDF-1.7\nprotected topic content'), save=True)

    def test_student_read_access_is_preserved_for_assigned_grade(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('Topics'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reading')

    def test_topic_page_requires_authentication(self):
        response = self.client.get(reverse('Topics'))

        self.assertEqual(response.status_code, 302)

    def test_topic_file_requires_authentication(self):
        response = self.client.get(reverse('TopicFile', args=[self.topic.pk]))

        self.assertEqual(response.status_code, 302)

    @override_settings(DEBUG=True)
    def test_debug_media_url_cannot_bypass_topic_file_authorization(self):
        media_url = self.topic.topic_file.url

        anonymous_response = self.client.get(media_url)
        self.assertEqual(anonymous_response.status_code, 302)

        other_grade = GradeAndSection.objects.create(Grades='Grade 7')
        other_student = CustomUser.objects.create_user(
            username='media-other-student',
            password='test-password-123',
            student_grade_level=other_grade,
        )
        self.client.force_login(other_student)
        denied_response = self.client.get(media_url)

        self.assertEqual(denied_response.status_code, 404)

    def test_matching_grade_student_can_read_and_download_topic_file(self):
        self.client.force_login(self.student)

        read_response = self.client.get(reverse('TopicFile', args=[self.topic.pk]))
        download_response = self.client.get(reverse('TopicFile', args=[self.topic.pk]), {'download': '1'})

        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(b''.join(read_response.streaming_content), b'%PDF-1.7\nprotected topic content')
        self.assertEqual(read_response['Content-Type'], 'application/pdf')
        self.assertIn('inline', read_response['Content-Disposition'])
        self.assertEqual(read_response['Cache-Control'], 'private, no-store')
        self.assertEqual(download_response.status_code, 200)
        self.assertIn('attachment', download_response['Content-Disposition'])

    def test_cross_grade_and_unassigned_students_cannot_read_topic_file(self):
        another_grade = GradeAndSection.objects.create(Grades='Grade 7')
        other_student = CustomUser.objects.create_user(
            username='other-student',
            password='test-password-123',
            student_grade_level=another_grade,
        )
        unassigned_student = CustomUser.objects.create_user(
            username='unassigned-student',
            password='test-password-123',
        )

        for student in (other_student, unassigned_student):
            with self.subTest(username=student.username):
                self.client.force_login(student)
                response = self.client.get(reverse('TopicFile', args=[self.topic.pk]))
                self.assertEqual(response.status_code, 404)

    def test_staff_can_read_topic_files_for_any_grade(self):
        other_grade = GradeAndSection.objects.create(Grades='Grade 8')
        other_topic = TopicRecord.objects.create(
            topic='Advanced reading',
            subject='English',
            grade_level=other_grade,
            topic_file='fixture-other.pdf',
        )
        other_topic.topic_file.save('advanced.pdf', ContentFile(b'%PDF-1.7\nstaff content'), save=True)
        self.client.force_login(self.staff)

        response = self.client.get(reverse('TopicFile', args=[other_topic.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.7\nstaff content')

    def test_unassigned_student_sees_no_topics(self):
        unassigned_student = CustomUser.objects.create_user(
            username='list-unassigned',
            password='test-password-123',
        )
        self.client.force_login(unassigned_student)

        response = self.client.get(reverse('Topics'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Reading')

    def test_topic_list_uses_protected_urls_without_google_viewer_or_media_url(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('Topics'))

        self.assertContains(response, reverse('TopicFile', args=[self.topic.pk]))
        self.assertNotContains(response, 'docs.google.com/viewer')
        self.assertNotContains(response, self.topic.topic_file.url)

    def test_anonymous_user_cannot_upload_update_or_delete_topics(self):
        upload_response = self.client.post(reverse('Topics'), {
            'topic': 'Anonymous topic',
            'subject': 'English',
            'grade_level': self.grade.pk,
            'topic_file': SimpleUploadedFile('anonymous.pdf', b'test'),
        })
        update_response = self.client.post(
            reverse('UpdateTopic', args=[self.topic.pk]),
            {'topic': 'Anonymous edit', 'subject': 'English'},
        )
        delete_response = self.client.post(reverse('DeleteTopics', args=[self.topic.pk]))

        self.assertEqual(upload_response.status_code, 302)
        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(TopicRecord.objects.filter(topic='Anonymous topic').exists())
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.topic, 'Reading')
        self.assertTrue(TopicRecord.objects.filter(pk=self.topic.pk).exists())

    def test_non_staff_cannot_create_topics(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse('Topics'), {
            'topic': 'Unauthorized topic',
            'subject': 'English',
            'grade_level': self.grade.pk,
            'topic_file': SimpleUploadedFile('notes.pdf', b'test'),
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(TopicRecord.objects.filter(topic='Unauthorized topic').exists())

    def test_staff_can_create_topics(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Topics'), {
            'topic': 'Authorized topic',
            'subject': 'English',
            'grade_level': self.grade.pk,
            'topic_file': SimpleUploadedFile('notes.pdf', b'%PDF-1.7\n'),
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TopicRecord.objects.filter(topic='Authorized topic').exists())

    def test_topic_upload_accepts_pdf_docx_and_pptx_signatures(self):
        validate_topic_file(SimpleUploadedFile('notes.pdf', b'%PDF-1.7\n'))

        for name, required_member in (
            ('notes.docx', 'word/document.xml'),
            ('slides.pptx', 'ppt/presentation.xml'),
        ):
            with self.subTest(name=name):
                document = BytesIO()
                with ZipFile(document, 'w') as package:
                    package.writestr('[Content_Types].xml', '<Types/>')
                    package.writestr(required_member, '<document/>')
                validate_topic_file(SimpleUploadedFile(name, document.getvalue()))

    def test_topic_upload_rejects_wrong_extension_content_and_oversized_files(self):
        with self.assertRaises(ValidationError):
            validate_topic_file(SimpleUploadedFile('notes.exe', b'%PDF-1.7'))
        with self.assertRaises(ValidationError):
            validate_topic_file(SimpleUploadedFile('notes.pdf', b'<html>not a PDF</html>'))

        oversized_file = SimpleUploadedFile('notes.pdf', b'%PDF-1.7')
        oversized_file.size = MAX_TOPIC_FILE_BYTES + 1
        with self.assertRaises(ValidationError):
            validate_topic_file(oversized_file)

    def test_staff_sees_topic_upload_validation_errors_without_server_error(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Topics'), {
            'topic': 'Invalid upload',
            'subject': 'English',
            'grade_level': self.grade.pk,
            'topic_file': SimpleUploadedFile('notes.pdf', b'<html>not a PDF</html>'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The file content is not a PDF')
        self.assertFalse(TopicRecord.objects.filter(topic='Invalid upload').exists())

    def test_topic_admin_rejects_invalid_file_content(self):
        administrator = CustomUser.objects.create_superuser(
            username='administrator',
            password='test-password-123',
        )
        self.client.force_login(administrator)

        response = self.client.post(reverse('admin:Topics_topicrecord_add'), {
            'topic': 'Admin upload',
            'subject': 'English',
            'grade_level': self.grade.pk,
            'topic_file': SimpleUploadedFile('notes.pdf', b'<html>not a PDF</html>'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The file content is not a PDF')
        self.assertFalse(TopicRecord.objects.filter(topic='Admin upload').exists())

    def test_non_staff_cannot_update_or_delete_topics(self):
        self.client.force_login(self.student)

        update_response = self.client.post(
            reverse('UpdateTopic', args=[self.topic.pk]),
            {'topic': 'Changed', 'subject': 'English'},
        )
        delete_response = self.client.post(reverse('DeleteTopics', args=[self.topic.pk]))

        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.topic, 'Reading')
        self.assertTrue(TopicRecord.objects.filter(pk=self.topic.pk).exists())

    def test_topic_delete_is_post_only_and_staff_can_delete(self):
        self.client.force_login(self.staff)

        get_response = self.client.get(reverse('DeleteTopics', args=[self.topic.pk]))
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(TopicRecord.objects.filter(pk=self.topic.pk).exists())

        post_response = self.client.post(reverse('DeleteTopics', args=[self.topic.pk]))
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(TopicRecord.objects.filter(pk=self.topic.pk).exists())

    def test_topic_delete_form_includes_csrf_token(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('Topics'))

        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_topic_update_rejects_missing_csrf_and_accepts_valid_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        update_url = reverse('UpdateTopic', args=[self.topic.pk])
        csrf_client.get(update_url)

        rejected = csrf_client.post(update_url, {'topic': 'Rejected update', 'subject': 'English'})

        self.assertEqual(rejected.status_code, 403)
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.topic, 'Reading')

        token = csrf_client.cookies['csrftoken'].value
        accepted = csrf_client.post(
            update_url,
            {'topic': 'Updated topic', 'subject': 'English'},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(accepted.status_code, 302)
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.topic, 'Updated topic')

    def test_delete_rejects_missing_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)

        csrf_client.get(reverse('Topics'))
        response = csrf_client.post(reverse('DeleteTopics', args=[self.topic.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(TopicRecord.objects.filter(pk=self.topic.pk).exists())
