from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from circuits.choices import *
from circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from dcim.models import Site
from extras.models import Graph
from utilities.testing import APITestCase, APIViewTestCases


class AppTest(APITestCase):

    def test_root(self):
        url = reverse('circuits-api:api-root')
        response = self.client.get('{}?format=api'.format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class ProviderTest(APIViewTestCases.APIViewTestCase):
    model = Provider
    brief_fields = ['circuit_count', 'id', 'name', 'slug', 'url']
    create_data = [
        {
            'name': 'Provider 4',
            'slug': 'provider-4',
        },
        {
            'name': 'Provider 5',
            'slug': 'provider-5',
        },
        {
            'name': 'Provider 6',
            'slug': 'provider-6',
        },
    ]

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider(name='Provider 1', slug='provider-1'),
            Provider(name='Provider 2', slug='provider-2'),
            Provider(name='Provider 3', slug='provider-3'),
        )
        Provider.objects.bulk_create(providers)

    def test_get_provider_graphs(self):
        """
        Test retrieval of Graphs assigned to Providers.
        """
        provider = self.model.objects.first()
        ct = ContentType.objects.get(app_label='circuits', model='provider')
        graphs = (
            Graph(type=ct, name='Graph 1', source='http://example.com/graphs.py?provider={{ obj.slug }}&foo=1'),
            Graph(type=ct, name='Graph 2', source='http://example.com/graphs.py?provider={{ obj.slug }}&foo=2'),
            Graph(type=ct, name='Graph 3', source='http://example.com/graphs.py?provider={{ obj.slug }}&foo=3'),
        )
        Graph.objects.bulk_create(graphs)

        url = reverse('circuits-api:provider-graphs', kwargs={'pk': provider.pk})
        response = self.client.get(url, **self.header)

        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['embed_url'], 'http://example.com/graphs.py?provider=provider-1&foo=1')


class CircuitTypeTest(APIViewTestCases.APIViewTestCase):
    model = CircuitType
    brief_fields = ['circuit_count', 'id', 'name', 'slug', 'url']
    create_data = (
        {
            'name': 'Circuit Type 4',
            'slug': 'circuit-type-4',
        },
        {
            'name': 'Circuit Type 5',
            'slug': 'circuit-type-5',
        },
        {
            'name': 'Circuit Type 6',
            'slug': 'circuit-type-6',
        },
    )

    @classmethod
    def setUpTestData(cls):

        circuit_types = (
            CircuitType(name='Circuit Type 1', slug='circuit-type-1'),
            CircuitType(name='Circuit Type 2', slug='circuit-type-2'),
            CircuitType(name='Circuit Type 3', slug='circuit-type-3'),
        )
        CircuitType.objects.bulk_create(circuit_types)


class CircuitTest(APIViewTestCases.APIViewTestCase):
    model = Circuit
    brief_fields = ['cid', 'id', 'url']

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider(name='Provider 1', slug='provider-1'),
            Provider(name='Provider 2', slug='provider-2'),
        )
        Provider.objects.bulk_create(providers)

        circuit_types = (
            CircuitType(name='Circuit Type 1', slug='circuit-type-1'),
            CircuitType(name='Circuit Type 2', slug='circuit-type-2'),
        )
        CircuitType.objects.bulk_create(circuit_types)

        circuits = (
            Circuit(cid='Circuit 1', provider=providers[0], type=circuit_types[0]),
            Circuit(cid='Circuit 2', provider=providers[0], type=circuit_types[0]),
            Circuit(cid='Circuit 3', provider=providers[0], type=circuit_types[0]),
        )
        Circuit.objects.bulk_create(circuits)

        cls.create_data = [
            {
                'cid': 'Circuit 4',
                'provider': providers[1].pk,
                'type': circuit_types[1].pk,
            },
            {
                'cid': 'Circuit 5',
                'provider': providers[1].pk,
                'type': circuit_types[1].pk,
            },
            {
                'cid': 'Circuit 6',
                'provider': providers[1].pk,
                'type': circuit_types[1].pk,
            },
        ]


class CircuitTerminationTest(APIViewTestCases.APIViewTestCase):
    model = CircuitTermination
    brief_fields = ['circuit', 'id', 'term_side', 'url']

    @classmethod
    def setUpTestData(cls):
        SIDE_A = CircuitTerminationSideChoices.SIDE_A
        SIDE_Z = CircuitTerminationSideChoices.SIDE_Z

        sites = (
            Site(name='Site 1', slug='site-1'),
            Site(name='Site 2', slug='site-2'),
        )
        Site.objects.bulk_create(sites)

        provider = Provider.objects.create(name='Provider 1', slug='provider-1')
        circuit_type = CircuitType.objects.create(name='Circuit Type 1', slug='circuit-type-1')

        circuits = (
            Circuit(cid='Circuit 1', provider=provider, type=circuit_type),
            Circuit(cid='Circuit 2', provider=provider, type=circuit_type),
            Circuit(cid='Circuit 3', provider=provider, type=circuit_type),
        )
        Circuit.objects.bulk_create(circuits)

        circuit_terminations = (
            CircuitTermination(circuit=circuits[0], site=sites[0], port_speed=100000, term_side=SIDE_A),
            CircuitTermination(circuit=circuits[0], site=sites[1], port_speed=100000, term_side=SIDE_Z),
            CircuitTermination(circuit=circuits[1], site=sites[0], port_speed=100000, term_side=SIDE_A),
            CircuitTermination(circuit=circuits[1], site=sites[1], port_speed=100000, term_side=SIDE_Z),
        )
        CircuitTermination.objects.bulk_create(circuit_terminations)

        cls.create_data = [
            {
                'circuit': circuits[2].pk,
                'term_side': SIDE_A,
                'site': sites[1].pk,
                'port_speed': 200000,
            },
            {
                'circuit': circuits[2].pk,
                'term_side': SIDE_Z,
                'site': sites[1].pk,
                'port_speed': 200000,
            },
        ]
