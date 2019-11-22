from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from change.models import ChangedField, ChangeInformation
from change.views import ChangeFormView


class ChangeTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('change', 'change@ch.ng', 'change')

    def tearDown(self):
        self.user.delete()

    def test_toggle_change_not_logged_in(self):
        url = reverse('change:change_toggle')
        response = self.client.get(url)
        self.assertRedirects(response, "/login/?next={}".format(url))
        self.assertIsNone(self.client.session.get("in_change"))

    def test_toggle_change(self):
        url = reverse('change:change_toggle')
        self.client.login(username='change', password='change')
        self.assertIsNone(self.client.session.get("in_change"))
        response = self.client.get(url)
        self.assertTrue(self.client.session["in_change"])
        response = self.client.get(url)

    def test_toggle_change_twice_empty_change(self):
        url = reverse('change:change_toggle')
        self.client.login(username='change', password='change')
        response = self.client.get(url)
        response = self.client.get(url)
        self.assertFalse(self.client.session["in_change"])
        self.assertEquals(ChangedField.objects.count(), 0)

    def test_change_form_not_logged_in(self):
        url = reverse('change:change_form')
        response = self.client.get(url)
        self.assertRedirects(response, "/login/?next={}".format(url))

    def test_change_form_not_in_change(self):
        url = reverse('change:change_form')
        self.client.login(username='change', password='change')
        response = self.client.get(url)
        self.assertRedirects(response, "/")

    def test_change_form(self):
        self.client.login(username='change', password='change')
        url = reverse('change:change_toggle')
        self.client.get(url)
        url = reverse('change:change_form')
        response = self.client.get(url)
        self.assertIn('affected_customers', response.context)
        self.assertIn('return_url', response.context)
        self.assertIn('obj_type', response.context)
        self.assertIn('change/changeinformation_form.html',
                      [t.name for t in response.templates])
