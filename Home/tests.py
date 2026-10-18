import os
import subprocess
import sys
from pathlib import Path

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .admin import GradeAndSectionListAdmin
from .models import CustomUser, GradeAndSection, StudentAttendance


TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


class SecretKeyConfigurationTests(SimpleTestCase):
    def test_settings_refuse_to_start_without_secret_key_even_in_debug(self):
        environment = os.environ.copy()
        environment.pop('SECRET_KEY', None)
        environment['DJANGO_DEBUG'] = 'true'
        environment['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

        result = subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SECRET_KEY must be set.', result.stderr)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class StudentAttendanceAccessTests(TestCase):
    def setUp(self):
        self.current_grade = GradeAndSection.objects.create(Grades='Grade 6')
        self.requested_grade = GradeAndSection.objects.create(Grades='Grade 7')
        self.student = CustomUser.objects.create_user(
            username='student',
            password='test-password-123',
            first_name='Assigned Student',
            student_grade_level=self.current_grade,
        )
        self.other_student = CustomUser.objects.create_user(
            username='other-student',
            password='test-password-123',
            student_grade_level=self.current_grade,
        )

    def test_attendance_requires_authentication(self):
        response = self.client.get(reverse('Attendance'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudentAttendance.objects.count(), 0)

    def test_student_cannot_change_assigned_grade_or_attendance_identity(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse('Attendance'), {
            'Student_Name': 'Impersonated Student',
            'Grade_and_Section': self.requested_grade.pk,
            'user': self.other_student.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.other_student.refresh_from_db()
        self.assertEqual(self.student.student_grade_level, self.current_grade)
        self.assertEqual(self.other_student.student_grade_level, self.current_grade)
        self.assertEqual(StudentAttendance.objects.count(), 0)

    def test_attendance_uses_assigned_grade_and_authenticated_users_name(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse('Attendance'), {
            'Student_Name': 'Impersonated Student',
            'Grade_and_Section': self.current_grade.pk,
            'user': self.other_student.pk,
        })

        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_grade_level, self.current_grade)
        attendance = StudentAttendance.objects.get()
        self.assertEqual(attendance.Grade_and_Section, self.current_grade)
        self.assertEqual(attendance.Student_Name, 'Assigned Student')

    def test_unassigned_student_cannot_submit_attendance(self):
        unassigned_student = CustomUser.objects.create_user(username='unassigned')
        self.client.force_login(unassigned_student)

        response = self.client.post(reverse('Attendance'), {
            'Student_Name': 'Unassigned Student',
            'Grade_and_Section': self.requested_grade.pk,
        })

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Your grade and section has not been assigned', status_code=403)
        self.assertEqual(StudentAttendance.objects.count(), 0)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class LoginRateLimitTests(TestCase):
    def test_invalid_credentials_are_counted_once_and_locked_after_configured_limit(self):
        for attempt in range(5):
            response = self.client.post(reverse('Student'), {
                'username': 'synthetic-user',
                'password': 'incorrect-password',
            })

            expected_status = 429 if attempt == 4 else 200
            self.assertEqual(response.status_code, expected_status)


class GradeAndSectionAdminDeletionTests(TestCase):
    def test_only_superusers_can_delete_grade_sections_in_admin(self):
        staff = CustomUser.objects.create_user(username='admin-staff', is_staff=True)
        superuser = CustomUser.objects.create_superuser(username='principal', password='test-password-123')
        model_admin = GradeAndSectionListAdmin(GradeAndSection, admin.site)
        request_factory = RequestFactory()

        staff_request = request_factory.get('/admin/Home/gradeandsection/')
        staff_request.user = staff
        superuser_request = request_factory.get('/admin/Home/gradeandsection/')
        superuser_request.user = superuser

        self.assertFalse(model_admin.has_delete_permission(staff_request))
        self.assertTrue(model_admin.has_delete_permission(superuser_request))


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class AccountRegistrationAuthorizationTests(TestCase):
    def test_anonymous_cannot_register_accounts(self):
        response = self.client.post(reverse('Register'), {
            'first_name': 'Untrusted',
            'username': 'untrusted-user',
            'password1': 'Synthetic-password-123',
            'password2': 'Synthetic-password-123',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomUser.objects.filter(username='untrusted-user').exists())

    def test_non_staff_cannot_register_accounts(self):
        student = CustomUser.objects.create_user(username='student', password='test-password-123')
        self.client.force_login(student)

        response = self.client.post(reverse('Register'), {
            'first_name': 'Untrusted',
            'username': 'untrusted-user',
            'password1': 'Synthetic-password-123',
            'password2': 'Synthetic-password-123',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomUser.objects.filter(username='untrusted-user').exists())
