from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from change.models import ChangedField


class ChangeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('change', 'change@ch.ng', 'change')

    def tearDown(self):
        self.user.delete()

    def test_toggle_change_not_logged_in(self):
        url = reverse('change:toggle')
        response = self.client.get(url)
        self.assertRedirects(response, "/login/?next=/change/toggle/")
        self.assertIsNone(self.client.session.get("in_change"))

    def test_toggle_change(self):
        url = reverse('change:toggle')
        self.client.login(username='change', password='change')
        self.assertIsNone(self.client.session.get("in_change"))
        response = self.client.get(url)
        self.assertTrue(self.client.session["in_change"])
        response = self.client.get(url)

    def test_toggle_change_twice_empty_change(self):
        url = reverse('change:toggle')
        self.client.login(username='change', password='change')
        response = self.client.get(url)
        response = self.client.get(url)
        self.assertFalse(self.client.session["in_change"])
        self.assertEquals(ChangedField.objects.count(), 0)
