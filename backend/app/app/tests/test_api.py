import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()

CSRF_URL = reverse('api:get_csrf_token')
BOARDS_URL = reverse('api:boards')


class CsrfTokenTests(TestCase):
    """Test the CSRF token endpoint."""

    def setUp(self):
        self.client = Client()

    def test_get_csrf_token_returns_204(self):
        """Test that GET /api/csrf/ returns 204 No Content."""
        res = self.client.get(CSRF_URL)
        self.assertEqual(res.status_code, 204)

    def test_get_csrf_token_sets_cookie(self):
        """Test that GET /api/csrf/ sets a CSRF cookie."""
        res = self.client.get(CSRF_URL)
        self.assertIn('csrftoken', res.cookies)


class IntegrityErrorHandlerTests(TestCase):
    """Test the global IntegrityError exception handler."""

    def setUp(self):
        self.user = User.objects.create_user('testuser@example.com')
        self.client = Client()
        self.client.force_login(self.user)

    def test_integrity_error_returns_400(self):
        """Test that an IntegrityError raised in a view returns 400."""
        with patch(
            'board.models.Board.objects.create',
            side_effect=IntegrityError('unique constraint failed'),
        ):
            res = self.client.post(
                BOARDS_URL,
                data=json.dumps({'title': 'Test Board', 'columns': []}),
                content_type='application/json',
            )

        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            content['detail'],
            'Invalid data. Please check your input.',
        )
