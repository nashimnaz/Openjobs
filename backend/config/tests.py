from django.test import TestCase
from django.urls import reverse
from rest_framework import status


class HealthCheckEndpointTests(TestCase):
    def test_health_check_returns_healthy(self):
        url = reverse('health-check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('database'), 'healthy')
        self.assertEqual(data.get('service'), 'openjobs-backend')
