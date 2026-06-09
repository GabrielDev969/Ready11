from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(AXES_ENABLED=False)
class UserRegistrationTest(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_unverified_user(self):
        self.client.post(reverse('register'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'SecurePass1!',
            'confirm_password': 'SecurePass1!',
        })
        user = User.objects.filter(email='test@example.com').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.email_verified)

    def test_register_weak_password_rejected(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'weak@example.com',
            'password': 'password',
            'confirm_password': 'password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='weak@example.com').exists())


@override_settings(AXES_ENABLED=False)
class LoginTest(TestCase):
    def setUp(self):
        self.verified_user = User.objects.create_user(
            email='verified@example.com',
            password='SecurePass1!',
            first_name='Verified',
            last_name='User',
            is_active=True,
            email_verified=True,
        )
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='SecurePass1!',
            first_name='Unverified',
            last_name='User',
            is_active=True,
            email_verified=False,
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_verified_user_succeeds(self):
        self.client.post(reverse('login'), {
            'email': 'verified@example.com',
            'password': 'SecurePass1!',
        })
        response = self.client.get(reverse('login'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_unverified_user_blocked(self):
        self.client.post(reverse('login'), {
            'email': 'unverified@example.com',
            'password': 'SecurePass1!',
        })
        response = self.client.get(reverse('login'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_wrong_password_fails(self):
        self.client.post(reverse('login'), {
            'email': 'verified@example.com',
            'password': 'WrongPassword1!',
        })
        response = self.client.get(reverse('login'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


@override_settings(AXES_ENABLED=False)
class PasswordResetTest(TestCase):
    def test_reset_request_page_loads(self):
        response = self.client.get(reverse('password_reset_request'))
        self.assertEqual(response.status_code, 200)

    def test_reset_request_always_redirects_to_done(self):
        response = self.client.post(reverse('password_reset_request'), {
            'email': 'nonexistent@example.com',
        })
        self.assertRedirects(response, reverse('password_reset_done'))

    def test_reset_request_existing_email_also_redirects_to_done(self):
        User.objects.create_user(
            email='exists@example.com',
            password='SecurePass1!',
            first_name='A',
            last_name='B',
            is_active=True,
            email_verified=True,
        )
        response = self.client.post(reverse('password_reset_request'), {
            'email': 'exists@example.com',
        })
        self.assertRedirects(response, reverse('password_reset_done'))

    def test_reset_confirm_invalid_link_shows_error(self):
        response = self.client.get(reverse('password_reset_confirm', kwargs={
            'uidb64': 'invalid',
            'token': 'invalid-token',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid')

    def test_reset_complete_page_loads(self):
        response = self.client.get(reverse('password_reset_complete'))
        self.assertEqual(response.status_code, 200)
