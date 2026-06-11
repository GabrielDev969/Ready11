from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

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
class LanguagePreferenceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='lang@example.com',
            password='SecurePass1!',
            first_name='Lang',
            last_name='User',
            is_active=True,
            email_verified=True,
        )
        self.client.force_login(self.user)

    def test_language_switcher_persists_on_profile(self):
        self.client.post(reverse('set_language'), {'language': 'pt-br', 'next': '/'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'pt-br')

    def test_saved_language_is_applied_to_responses(self):
        self.user.language = 'pt-br'
        self.user.save(update_fields=['language'])
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.headers.get('Content-Language'), 'pt-br')

    def test_settings_language_form_saves(self):
        self.client.post(reverse('settings'), {'action': 'language', 'language': 'pt-br'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'pt-br')

    def test_profile_and_settings_pages_load(self):
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('settings')).status_code, 200)


@override_settings(AXES_ENABLED=False)
class TwoFactorSetupTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='2fa@example.com',
            password='SecurePass1!',
            first_name='Two',
            last_name='Factor',
            is_active=True,
            email_verified=True,
        )
        self.client.force_login(self.user)

    def test_full_setup_flow_confirms_device_and_creates_backup_codes(self):
        # GET creates the unconfirmed TOTP device and shows the QR code.
        response = self.client.get(reverse('2fa_setup'))
        self.assertEqual(response.status_code, 200)
        device = TOTPDevice.objects.get(user=self.user, confirmed=False)

        # POST with a valid current token confirms the device.
        token = f'{totp(device.bin_key):06d}'
        response = self.client.post(reverse('2fa_setup'), {'token': token})
        self.assertRedirects(response, reverse('2fa_backup_codes'))

        device.refresh_from_db()
        self.assertTrue(device.confirmed)

        static_device = StaticDevice.objects.get(user=self.user, confirmed=True)
        self.assertEqual(static_device.token_set.count(), 8)

    def test_invalid_token_does_not_confirm(self):
        self.client.get(reverse('2fa_setup'))
        response = self.client.post(reverse('2fa_setup'), {'token': '000000'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())


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
