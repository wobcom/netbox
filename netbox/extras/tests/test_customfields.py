from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status

from dcim.forms import SiteCSVForm
from dcim.models import Site
from extras.choices import *
from extras.models import CustomField, CustomFieldValue, CustomFieldChoice
from utilities.testing import APITestCase, create_test_user
from virtualization.models import VirtualMachine


class CustomFieldTest(TestCase):

    def setUp(self):

        Site.objects.bulk_create([
            Site(name='Site A', slug='site-a'),
            Site(name='Site B', slug='site-b'),
            Site(name='Site C', slug='site-c'),
        ])

    def test_simple_fields(self):

        DATA = (
            {'field_type': CustomFieldTypeChoices.TYPE_TEXT, 'field_value': 'Foobar!', 'empty_value': ''},
            {'field_type': CustomFieldTypeChoices.TYPE_INTEGER, 'field_value': 0, 'empty_value': None},
            {'field_type': CustomFieldTypeChoices.TYPE_INTEGER, 'field_value': 42, 'empty_value': None},
            {'field_type': CustomFieldTypeChoices.TYPE_BOOLEAN, 'field_value': True, 'empty_value': None},
            {'field_type': CustomFieldTypeChoices.TYPE_BOOLEAN, 'field_value': False, 'empty_value': None},
            {'field_type': CustomFieldTypeChoices.TYPE_DATE, 'field_value': date(2016, 6, 23), 'empty_value': None},
            {'field_type': CustomFieldTypeChoices.TYPE_URL, 'field_value': 'http://example.com/', 'empty_value': ''},
        )

        obj_type = ContentType.objects.get_for_model(Site)

        for data in DATA:

            # Create a custom field
            cf = CustomField(type=data['field_type'], name='my_field', required=False)
            cf.save()
            cf.obj_type.set([obj_type])
            cf.save()

            # Assign a value to the first Site
            site = Site.objects.first()
            cfv = CustomFieldValue(field=cf, obj_type=obj_type, obj_id=site.id)
            cfv.value = data['field_value']
            cfv.save()

            # Retrieve the stored value
            cfv = CustomFieldValue.objects.filter(obj_type=obj_type, obj_id=site.pk).first()
            self.assertEqual(cfv.value, data['field_value'])

            # Delete the stored value
            cfv.value = data['empty_value']
            cfv.save()
            self.assertEqual(CustomFieldValue.objects.filter(obj_type=obj_type, obj_id=site.pk).count(), 0)

            # Delete the custom field
            cf.delete()

    def test_select_field(self):

        obj_type = ContentType.objects.get_for_model(Site)

        # Create a custom field
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_SELECT, name='my_field', required=False)
        cf.save()
        cf.obj_type.set([obj_type])
        cf.save()

        # Create some choices for the field
        CustomFieldChoice.objects.bulk_create([
            CustomFieldChoice(field=cf, value='Option A'),
            CustomFieldChoice(field=cf, value='Option B'),
            CustomFieldChoice(field=cf, value='Option C'),
        ])

        # Assign a value to the first Site
        site = Site.objects.first()
        cfv = CustomFieldValue(field=cf, obj_type=obj_type, obj_id=site.id)
        cfv.value = cf.choices.first()
        cfv.save()

        # Retrieve the stored value
        cfv = CustomFieldValue.objects.filter(obj_type=obj_type, obj_id=site.pk).first()
        self.assertEqual(str(cfv.value), 'Option A')

        # Delete the stored value
        cfv.value = None
        cfv.save()
        self.assertEqual(CustomFieldValue.objects.filter(obj_type=obj_type, obj_id=site.pk).count(), 0)

        # Delete the custom field
        cf.delete()


class CustomFieldAPITest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Site)

        # Text custom field
        cls.cf_text = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name='text_field', default='foo')
        cls.cf_text.save()
        cls.cf_text.obj_type.set([content_type])

        # Integer custom field
        cls.cf_integer = CustomField(type=CustomFieldTypeChoices.TYPE_INTEGER, name='number_field', default=123)
        cls.cf_integer.save()
        cls.cf_integer.obj_type.set([content_type])

        # Boolean custom field
        cls.cf_boolean = CustomField(type=CustomFieldTypeChoices.TYPE_BOOLEAN, name='boolean_field', default=False)
        cls.cf_boolean.save()
        cls.cf_boolean.obj_type.set([content_type])

        # Date custom field
        cls.cf_date = CustomField(type=CustomFieldTypeChoices.TYPE_DATE, name='date_field', default='2020-01-01')
        cls.cf_date.save()
        cls.cf_date.obj_type.set([content_type])

        # URL custom field
        cls.cf_url = CustomField(type=CustomFieldTypeChoices.TYPE_URL, name='url_field', default='http://example.com/1')
        cls.cf_url.save()
        cls.cf_url.obj_type.set([content_type])

        # Select custom field
        cls.cf_select = CustomField(type=CustomFieldTypeChoices.TYPE_SELECT, name='choice_field')
        cls.cf_select.save()
        cls.cf_select.obj_type.set([content_type])
        cls.cf_select_choice1 = CustomFieldChoice(field=cls.cf_select, value='Foo')
        cls.cf_select_choice1.save()
        cls.cf_select_choice2 = CustomFieldChoice(field=cls.cf_select, value='Bar')
        cls.cf_select_choice2.save()
        cls.cf_select_choice3 = CustomFieldChoice(field=cls.cf_select, value='Baz')
        cls.cf_select_choice3.save()

        cls.cf_select.default = cls.cf_select_choice1.value
        cls.cf_select.save()

        # Create some sites
        cls.sites = (
            Site(name='Site 1', slug='site-1'),
            Site(name='Site 2', slug='site-2'),
        )
        Site.objects.bulk_create(cls.sites)

        # Assign custom field values for site 2
        site2_cfvs = {
            cls.cf_text: 'bar',
            cls.cf_integer: 456,
            cls.cf_boolean: True,
            cls.cf_date: '2020-01-02',
            cls.cf_url: 'http://example.com/2',
            cls.cf_select: cls.cf_select_choice2.pk,
        }
        for field, value in site2_cfvs.items():
            cfv = CustomFieldValue(field=field, obj=cls.sites[1])
            cfv.value = value
            cfv.save()

    def test_get_single_object_without_custom_field_values(self):
        """
        Validate that custom fields are present on an object even if it has no values defined.
        """
        url = reverse('dcim-api:site-detail', kwargs={'pk': self.sites[0].pk})
        response = self.client.get(url, **self.header)

        self.assertEqual(response.data['name'], self.sites[0].name)
        self.assertEqual(response.data['custom_fields'], {
            'text_field': None,
            'number_field': None,
            'boolean_field': None,
            'date_field': None,
            'url_field': None,
            'choice_field': None,
        })

    def test_get_single_object_with_custom_field_values(self):
        """
        Validate that custom fields are present and correctly set for an object with values defined.
        """
        site2_cfvs = {
            cfv.field.name: cfv.value for cfv in self.sites[1].custom_field_values.all()
        }

        url = reverse('dcim-api:site-detail', kwargs={'pk': self.sites[1].pk})
        response = self.client.get(url, **self.header)

        self.assertEqual(response.data['name'], self.sites[1].name)
        self.assertEqual(response.data['custom_fields']['text_field'], site2_cfvs['text_field'])
        self.assertEqual(response.data['custom_fields']['number_field'], site2_cfvs['number_field'])
        self.assertEqual(response.data['custom_fields']['boolean_field'], site2_cfvs['boolean_field'])
        self.assertEqual(response.data['custom_fields']['date_field'], site2_cfvs['date_field'])
        self.assertEqual(response.data['custom_fields']['url_field'], site2_cfvs['url_field'])
        self.assertEqual(response.data['custom_fields']['choice_field']['label'], self.cf_select_choice2.value)

    def test_create_single_object_with_defaults(self):
        """
        Create a new site with no specified custom field values and check that it received the default values.
        """
        data = {
            'name': 'Site 3',
            'slug': 'site-3',
        }

        url = reverse('dcim-api:site-list')
        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data['custom_fields']
        self.assertEqual(response_cf['text_field'], self.cf_text.default)
        self.assertEqual(response_cf['number_field'], self.cf_integer.default)
        self.assertEqual(response_cf['boolean_field'], self.cf_boolean.default)
        self.assertEqual(response_cf['date_field'], self.cf_date.default)
        self.assertEqual(response_cf['url_field'], self.cf_url.default)
        self.assertEqual(response_cf['choice_field'], self.cf_select_choice1.pk)

        # Validate database data
        site = Site.objects.get(pk=response.data['id'])
        cfvs = {
            cfv.field.name: cfv.value for cfv in site.custom_field_values.all()
        }
        self.assertEqual(cfvs['text_field'], self.cf_text.default)
        self.assertEqual(cfvs['number_field'], self.cf_integer.default)
        self.assertEqual(cfvs['boolean_field'], self.cf_boolean.default)
        self.assertEqual(str(cfvs['date_field']), self.cf_date.default)
        self.assertEqual(cfvs['url_field'], self.cf_url.default)
        self.assertEqual(cfvs['choice_field'].pk, self.cf_select_choice1.pk)

    def test_create_single_object_with_values(self):
        """
        Create a single new site with a value for each type of custom field.
        """
        data = {
            'name': 'Site 3',
            'slug': 'site-3',
            'custom_fields': {
                'text_field': 'bar',
                'number_field': 456,
                'boolean_field': True,
                'date_field': '2020-01-02',
                'url_field': 'http://example.com/2',
                'choice_field': self.cf_select_choice2.pk,
            },
        }

        url = reverse('dcim-api:site-list')
        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data['custom_fields']
        data_cf = data['custom_fields']
        self.assertEqual(response_cf['text_field'], data_cf['text_field'])
        self.assertEqual(response_cf['number_field'], data_cf['number_field'])
        self.assertEqual(response_cf['boolean_field'], data_cf['boolean_field'])
        self.assertEqual(response_cf['date_field'], data_cf['date_field'])
        self.assertEqual(response_cf['url_field'], data_cf['url_field'])
        self.assertEqual(response_cf['choice_field'], data_cf['choice_field'])

        # Validate database data
        site = Site.objects.get(pk=response.data['id'])
        cfvs = {
            cfv.field.name: cfv.value for cfv in site.custom_field_values.all()
        }
        self.assertEqual(cfvs['text_field'], data_cf['text_field'])
        self.assertEqual(cfvs['number_field'], data_cf['number_field'])
        self.assertEqual(cfvs['boolean_field'], data_cf['boolean_field'])
        self.assertEqual(str(cfvs['date_field']), data_cf['date_field'])
        self.assertEqual(cfvs['url_field'], data_cf['url_field'])
        self.assertEqual(cfvs['choice_field'].pk, data_cf['choice_field'])

    def test_create_multiple_objects_with_defaults(self):
        """
        Create three news sites with no specified custom field values and check that each received
        the default custom field values.
        """
        data = (
            {
                'name': 'Site 3',
                'slug': 'site-3',
            },
            {
                'name': 'Site 4',
                'slug': 'site-4',
            },
            {
                'name': 'Site 5',
                'slug': 'site-5',
            },
        )

        url = reverse('dcim-api:site-list')
        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, obj in enumerate(data):

            # Validate response data
            response_cf = response.data[i]['custom_fields']
            self.assertEqual(response_cf['text_field'], self.cf_text.default)
            self.assertEqual(response_cf['number_field'], self.cf_integer.default)
            self.assertEqual(response_cf['boolean_field'], self.cf_boolean.default)
            self.assertEqual(response_cf['date_field'], self.cf_date.default)
            self.assertEqual(response_cf['url_field'], self.cf_url.default)
            self.assertEqual(response_cf['choice_field'], self.cf_select_choice1.pk)

            # Validate database data
            site = Site.objects.get(pk=response.data[i]['id'])
            cfvs = {
                cfv.field.name: cfv.value for cfv in site.custom_field_values.all()
            }
            self.assertEqual(cfvs['text_field'], self.cf_text.default)
            self.assertEqual(cfvs['number_field'], self.cf_integer.default)
            self.assertEqual(cfvs['boolean_field'], self.cf_boolean.default)
            self.assertEqual(str(cfvs['date_field']), self.cf_date.default)
            self.assertEqual(cfvs['url_field'], self.cf_url.default)
            self.assertEqual(cfvs['choice_field'].pk, self.cf_select_choice1.pk)

    def test_create_multiple_objects_with_values(self):
        """
        Create a three new sites, each with custom fields defined.
        """
        custom_field_data = {
            'text_field': 'bar',
            'number_field': 456,
            'boolean_field': True,
            'date_field': '2020-01-02',
            'url_field': 'http://example.com/2',
            'choice_field': self.cf_select_choice2.pk,
        }
        data = (
            {
                'name': 'Site 3',
                'slug': 'site-3',
                'custom_fields': custom_field_data,
            },
            {
                'name': 'Site 4',
                'slug': 'site-4',
                'custom_fields': custom_field_data,
            },
            {
                'name': 'Site 5',
                'slug': 'site-5',
                'custom_fields': custom_field_data,
            },
        )

        url = reverse('dcim-api:site-list')
        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, obj in enumerate(data):

            # Validate response data
            response_cf = response.data[i]['custom_fields']
            self.assertEqual(response_cf['text_field'], custom_field_data['text_field'])
            self.assertEqual(response_cf['number_field'], custom_field_data['number_field'])
            self.assertEqual(response_cf['boolean_field'], custom_field_data['boolean_field'])
            self.assertEqual(response_cf['date_field'], custom_field_data['date_field'])
            self.assertEqual(response_cf['url_field'], custom_field_data['url_field'])
            self.assertEqual(response_cf['choice_field'], custom_field_data['choice_field'])

            # Validate database data
            site = Site.objects.get(pk=response.data[i]['id'])
            cfvs = {
                cfv.field.name: cfv.value for cfv in site.custom_field_values.all()
            }
            self.assertEqual(cfvs['text_field'], custom_field_data['text_field'])
            self.assertEqual(cfvs['number_field'], custom_field_data['number_field'])
            self.assertEqual(cfvs['boolean_field'], custom_field_data['boolean_field'])
            self.assertEqual(str(cfvs['date_field']), custom_field_data['date_field'])
            self.assertEqual(cfvs['url_field'], custom_field_data['url_field'])
            self.assertEqual(cfvs['choice_field'].pk, custom_field_data['choice_field'])

    def test_update_single_object_with_values(self):
        """
        Update an object with existing custom field values. Ensure that only the updated custom field values are
        modified.
        """
        site2_original_cfvs = {
            cfv.field.name: cfv.value for cfv in self.sites[1].custom_field_values.all()
        }
        data = {
            'custom_fields': {
                'text_field': 'ABCD',
                'number_field': 1234,
            },
        }

        url = reverse('dcim-api:site-detail', kwargs={'pk': self.sites[1].pk})
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        # Validate response data
        response_cf = response.data['custom_fields']
        data_cf = data['custom_fields']
        self.assertEqual(response_cf['text_field'], data_cf['text_field'])
        self.assertEqual(response_cf['number_field'], data_cf['number_field'])
        # TODO: Non-updated fields are missing from the response data
        # self.assertEqual(response_cf['boolean_field'], site2_original_cfvs['boolean_field'])
        # self.assertEqual(response_cf['date_field'], site2_original_cfvs['date_field'])
        # self.assertEqual(response_cf['url_field'], site2_original_cfvs['url_field'])
        # self.assertEqual(response_cf['choice_field']['label'], site2_original_cfvs['choice_field'].value)

        # Validate database data
        site2_updated_cfvs = {
            cfv.field.name: cfv.value for cfv in self.sites[1].custom_field_values.all()
        }
        self.assertEqual(site2_updated_cfvs['text_field'], data_cf['text_field'])
        self.assertEqual(site2_updated_cfvs['number_field'], data_cf['number_field'])
        self.assertEqual(site2_updated_cfvs['boolean_field'], site2_original_cfvs['boolean_field'])
        self.assertEqual(site2_updated_cfvs['date_field'], site2_original_cfvs['date_field'])
        self.assertEqual(site2_updated_cfvs['url_field'], site2_original_cfvs['url_field'])
        self.assertEqual(site2_updated_cfvs['choice_field'], site2_original_cfvs['choice_field'])


class CustomFieldChoiceAPITest(APITestCase):
    def setUp(self):
        super().setUp()

        vm_content_type = ContentType.objects.get_for_model(VirtualMachine)

        self.cf_1 = CustomField.objects.create(name="cf_1", type=CustomFieldTypeChoices.TYPE_SELECT)
        self.cf_2 = CustomField.objects.create(name="cf_2", type=CustomFieldTypeChoices.TYPE_SELECT)

        self.cf_choice_1 = CustomFieldChoice.objects.create(field=self.cf_1, value="cf_field_1", weight=100)
        self.cf_choice_2 = CustomFieldChoice.objects.create(field=self.cf_1, value="cf_field_2", weight=50)
        self.cf_choice_3 = CustomFieldChoice.objects.create(field=self.cf_2, value="cf_field_3", weight=10)

    def test_list_cfc(self):
        url = reverse('extras-api:custom-field-choice-list')
        response = self.client.get(url, **self.header)

        self.assertEqual(len(response.data), 2)
        self.assertEqual(len(response.data[self.cf_1.name]), 2)
        self.assertEqual(len(response.data[self.cf_2.name]), 1)

        self.assertTrue(self.cf_choice_1.value in response.data[self.cf_1.name])
        self.assertTrue(self.cf_choice_2.value in response.data[self.cf_1.name])
        self.assertTrue(self.cf_choice_3.value in response.data[self.cf_2.name])

        self.assertEqual(self.cf_choice_1.pk, response.data[self.cf_1.name][self.cf_choice_1.value])
        self.assertEqual(self.cf_choice_2.pk, response.data[self.cf_1.name][self.cf_choice_2.value])
        self.assertEqual(self.cf_choice_3.pk, response.data[self.cf_2.name][self.cf_choice_3.value])


class CustomFieldImportTest(TestCase):

    def setUp(self):

        user = create_test_user(
            permissions=[
                'dcim.view_site',
                'dcim.add_site',
            ]
        )
        self.client = Client()
        self.client.force_login(user)

    @classmethod
    def setUpTestData(cls):

        custom_fields = (
            CustomField(name='text', type=CustomFieldTypeChoices.TYPE_TEXT),
            CustomField(name='integer', type=CustomFieldTypeChoices.TYPE_INTEGER),
            CustomField(name='boolean', type=CustomFieldTypeChoices.TYPE_BOOLEAN),
            CustomField(name='date', type=CustomFieldTypeChoices.TYPE_DATE),
            CustomField(name='url', type=CustomFieldTypeChoices.TYPE_URL),
            CustomField(name='select', type=CustomFieldTypeChoices.TYPE_SELECT),
        )
        for cf in custom_fields:
            cf.save()
            cf.obj_type.set([ContentType.objects.get_for_model(Site)])

        CustomFieldChoice.objects.bulk_create((
            CustomFieldChoice(field=custom_fields[5], value='Choice A'),
            CustomFieldChoice(field=custom_fields[5], value='Choice B'),
            CustomFieldChoice(field=custom_fields[5], value='Choice C'),
        ))

    def test_import(self):
        """
        Import a Site in CSV format, including a value for each CustomField.
        """
        data = (
            ('name', 'slug', 'cf_text', 'cf_integer', 'cf_boolean', 'cf_date', 'cf_url', 'cf_select'),
            ('Site 1', 'site-1', 'ABC', '123', 'True', '2020-01-01', 'http://example.com/1', 'Choice A'),
            ('Site 2', 'site-2', 'DEF', '456', 'False', '2020-01-02', 'http://example.com/2', 'Choice B'),
            ('Site 3', 'site-3', '', '', '', '', '', ''),
        )
        csv_data = '\n'.join(','.join(row) for row in data)

        response = self.client.post(reverse('dcim:site_import'), {'csv': csv_data})
        self.assertEqual(response.status_code, 200)

        # Validate data for site 1
        custom_field_values = {
            cf.name: value for cf, value in Site.objects.get(name='Site 1').get_custom_fields().items()
        }
        self.assertEqual(len(custom_field_values), 6)
        self.assertEqual(custom_field_values['text'], 'ABC')
        self.assertEqual(custom_field_values['integer'], 123)
        self.assertEqual(custom_field_values['boolean'], True)
        self.assertEqual(custom_field_values['date'], date(2020, 1, 1))
        self.assertEqual(custom_field_values['url'], 'http://example.com/1')
        self.assertEqual(custom_field_values['select'].value, 'Choice A')

        # Validate data for site 2
        custom_field_values = {
            cf.name: value for cf, value in Site.objects.get(name='Site 2').get_custom_fields().items()
        }
        self.assertEqual(len(custom_field_values), 6)
        self.assertEqual(custom_field_values['text'], 'DEF')
        self.assertEqual(custom_field_values['integer'], 456)
        self.assertEqual(custom_field_values['boolean'], False)
        self.assertEqual(custom_field_values['date'], date(2020, 1, 2))
        self.assertEqual(custom_field_values['url'], 'http://example.com/2')
        self.assertEqual(custom_field_values['select'].value, 'Choice B')

        # No CustomFieldValues should be created for site 3
        obj_type = ContentType.objects.get_for_model(Site)
        site3 = Site.objects.get(name='Site 3')
        self.assertFalse(CustomFieldValue.objects.filter(obj_type=obj_type, obj_id=site3.pk).exists())
        self.assertEqual(CustomFieldValue.objects.count(), 12)  # Sanity check

    def test_import_missing_required(self):
        """
        Attempt to import an object missing a required custom field.
        """
        # Set one of our CustomFields to required
        CustomField.objects.filter(name='text').update(required=True)

        form_data = {
            'name': 'Site 1',
            'slug': 'site-1',
        }

        form = SiteCSVForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cf_text', form.errors)

    def test_import_invalid_choice(self):
        """
        Attempt to import an object with an invalid choice selection.
        """
        form_data = {
            'name': 'Site 1',
            'slug': 'site-1',
            'cf_select': 'Choice X'
        }

        form = SiteCSVForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cf_select', form.errors)
