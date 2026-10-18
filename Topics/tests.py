from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from Home.models import CustomUser, GradeAndSection
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

    def test_student_read_access_is_preserved_for_assigned_grade(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('Topics'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reading')

    def test_topic_page_requires_authentication(self):
        response = self.client.get(reverse('Topics'))

        self.assertEqual(response.status_code, 302)

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
            'topic_file': SimpleUploadedFile('notes.pdf', b'test'),
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TopicRecord.objects.filter(topic='Authorized topic').exists())

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
