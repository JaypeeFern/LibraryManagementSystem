from django.test import Client, TestCase, override_settings
from django.urls import reverse

from Home.models import CustomUser, GradeAndSection, StudentAttendance
from Topics.models import TopicRecord


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
class SectionAuthorizationTests(TestCase):
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
        self.section = GradeAndSection.objects.create(Grades='Grade 6')

    def test_anonymous_requests_cannot_create_update_or_delete_sections(self):
        create_response = self.client.post(reverse('Sections'), {'Grades': 'Grade 7'})
        update_response = self.client.post(
            reverse('UpdateSection', args=[self.section.pk]),
            {'Grades': 'Changed'},
        )
        delete_response = self.client.post(reverse('DeleteSection', args=[self.section.pk]))

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(GradeAndSection.objects.count(), 1)
        self.section.refresh_from_db()
        self.assertEqual(self.section.Grades, 'Grade 6')

    def test_staff_cannot_delete_cascading_section(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('DeleteSection', args=[self.section.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(GradeAndSection.objects.filter(pk=self.section.pk).exists())

    def test_section_delete_control_is_only_rendered_for_superusers(self):
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse('Sections'))
        superuser = CustomUser.objects.create_superuser(
            username='principal',
            password='test-password-123',
        )
        self.client.force_login(superuser)
        superuser_response = self.client.get(reverse('Sections'))

        self.assertNotContains(staff_response, 'data-form-url="/dashboard/home/system-users/sections/delete/')
        self.assertContains(superuser_response, 'data-form-url="/dashboard/home/system-users/sections/delete/')
        delete_response = self.client.get(reverse('DeleteSection', args=[self.section.pk]))
        self.assertContains(delete_response, 'permanently deletes its assigned student accounts, attendance records, and topics')

    def test_section_update_rejects_missing_csrf_and_accepts_valid_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        update_url = reverse('UpdateSection', args=[self.section.pk])
        csrf_client.get(update_url)

        rejected = csrf_client.post(update_url, {'Grades': 'Rejected'})

        self.assertEqual(rejected.status_code, 403)
        self.section.refresh_from_db()
        self.assertEqual(self.section.Grades, 'Grade 6')

        token = csrf_client.cookies['csrftoken'].value
        accepted = csrf_client.post(
            update_url,
            {'Grades': 'Grade 8'},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(accepted.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.Grades, 'Grade 8')

    def test_section_delete_rejects_missing_csrf(self):
        superuser = CustomUser.objects.create_superuser(
            username='principal',
            password='test-password-123',
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(superuser)
        delete_url = reverse('DeleteSection', args=[self.section.pk])
        csrf_client.get(delete_url)

        response = csrf_client.post(delete_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(GradeAndSection.objects.filter(pk=self.section.pk).exists())

    def test_superuser_section_delete_cascades_expected_synthetic_records(self):
        superuser = CustomUser.objects.create_superuser(
            username='principal',
            password='test-password-123',
        )
        assigned_student = CustomUser.objects.create_user(
            username='assigned-student',
            student_grade_level=self.section,
        )
        attendance = StudentAttendance.objects.create(
            Student_Name='Synthetic Student',
            Grade_and_Section=self.section,
        )
        topic = TopicRecord.objects.create(
            topic='Synthetic topic',
            subject='English',
            grade_level=self.section,
            topic_file='synthetic.pdf',
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(superuser)
        delete_url = reverse('DeleteSection', args=[self.section.pk])
        csrf_client.get(delete_url)
        token = csrf_client.cookies['csrftoken'].value

        response = csrf_client.post(delete_url, HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(GradeAndSection.objects.filter(pk=self.section.pk).exists())
        self.assertFalse(CustomUser.objects.filter(pk=assigned_student.pk).exists())
        self.assertFalse(StudentAttendance.objects.filter(pk=attendance.pk).exists())
        self.assertFalse(TopicRecord.objects.filter(pk=topic.pk).exists())

    def test_non_staff_cannot_create_sections(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse('Sections'), {'Grades': 'Grade 7'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(GradeAndSection.objects.count(), 1)

    def test_non_staff_cannot_update_or_delete_sections(self):
        self.client.force_login(self.student)

        update_response = self.client.post(
            reverse('UpdateSection', args=[self.section.pk]),
            {'Grades': 'Changed'},
        )
        delete_response = self.client.post(
            reverse('DeleteSection', args=[self.section.pk]),
        )

        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.Grades, 'Grade 6')
        self.assertTrue(GradeAndSection.objects.filter(pk=self.section.pk).exists())

    def test_staff_can_create_sections(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Sections'), {'Grades': 'Grade 7'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(GradeAndSection.objects.filter(Grades='Grade 7').exists())

    def test_editing_attendance_does_not_change_staff_grade_assignment(self):
        next_grade = GradeAndSection.objects.create(Grades='Grade 7')
        self.staff.student_grade_level = self.section
        self.staff.save(update_fields=['student_grade_level'])
        attendance = StudentAttendance.objects.create(
            Student_Name='Synthetic Student',
            Grade_and_Section=self.section,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('Edit', args=[attendance.pk]),
            {'Student_Name': 'Synthetic Student', 'Grade_and_Section': next_grade.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        attendance.refresh_from_db()
        self.assertEqual(self.staff.student_grade_level, self.section)
        self.assertEqual(attendance.Grade_and_Section, next_grade)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class AttendanceDeletionMethodTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username='teacher',
            password='test-password-123',
            is_staff=True,
        )
        self.grade = GradeAndSection.objects.create(Grades='Grade 6')
        self.attendance = StudentAttendance.objects.create(
            Student_Name='Student',
            Grade_and_Section=self.grade,
        )

    def test_attendance_delete_is_post_only(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('Delete', args=[self.attendance.pk]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(StudentAttendance.objects.filter(pk=self.attendance.pk).exists())

    def test_staff_can_delete_attendance_with_post(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('Delete', args=[self.attendance.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudentAttendance.objects.filter(pk=self.attendance.pk).exists())

    def test_system_users_delete_form_includes_csrf_token(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('System'))

        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_system_users_delete_rejects_missing_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        csrf_client.get(reverse('System'))

        response = csrf_client.post(reverse('Delete', args=[self.attendance.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(StudentAttendance.objects.filter(pk=self.attendance.pk).exists())


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGES,
)
class LogoutMethodTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='logout-student', password='test-password-123')

    def test_logout_is_post_only(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('Logout'))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_logout_rejects_missing_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_client.get(reverse('dashboard'))

        response = csrf_client.post(reverse('Logout'))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(csrf_client.session.get('_auth_user_id'))

    def test_logout_form_includes_csrf_token(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'name="csrfmiddlewaretoken"')
