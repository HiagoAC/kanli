from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from datetime import datetime, timedelta


class CleanupGuestsCommandTests(TestCase):
    def setUp(self):
        self.inactive_days = 10
        self.grace_period = 12
        self.dry_run = True
        self.out = StringIO()

    @patch('user.management.commands.cleanup_guests.cleanup_stale_guests')
    @patch('user.management.commands.cleanup_guests.cleanup_unused_guests')
    @patch('django.utils.timezone.now')
    def test_handle_calls_services_with_correct_args(
            self, mock_now, mock_cleanup_unused, mock_cleanup_stale):
        fixed_now = datetime(
            2026, 1, 16, 12, 0, 0, tzinfo=timezone.timezone.utc
        )
        mock_now.return_value = fixed_now
        mock_cleanup_stale.return_value = 3
        mock_cleanup_unused.return_value = 2

        call_command(
            'cleanup_guests',
            '--inactive-days', str(self.inactive_days),
            '--grace-period-new-accounts', str(self.grace_period),
            '--dry-run',
            stdout=self.out
        )

        cutoff = fixed_now - timedelta(days=self.inactive_days)
        mock_cleanup_stale.assert_called_once()
        _, kwargs = mock_cleanup_stale.call_args
        self.assertEqual(kwargs["cutoff"], cutoff)
        self.assertEqual(kwargs["dry_run"], self.dry_run)

        mock_cleanup_unused.assert_called_once()
        _, kwargs = mock_cleanup_unused.call_args
        self.assertEqual(
            kwargs["grace_period"],
            timedelta(hours=self.grace_period)
        )
        self.assertEqual(kwargs["dry_run"], self.dry_run)

    @patch('user.management.commands.cleanup_guests.cleanup_stale_guests')
    @patch('user.management.commands.cleanup_guests.cleanup_unused_guests')
    def test_handle_outputs_success_without_dry_run(
            self, mock_cleanup_unused, mock_cleanup_stale):
        """Test that a non-dry-run execution writes a SUCCESS message."""
        mock_cleanup_stale.return_value = 5
        mock_cleanup_unused.return_value = 2

        call_command(
            'cleanup_guests',
            '--inactive-days', str(self.inactive_days),
            '--grace-period-new-accounts', str(self.grace_period),
            stdout=self.out
        )

        output = self.out.getvalue()
        self.assertIn(
            'Deleted 5 stale guests and 2 unused new accounts', output)
        self.assertNotIn('[DRY RUN]', output)
