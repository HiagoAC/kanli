from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch
from board.models import Board
from user.pipeline import (
    create_default_board_pipeline,
    sync_user_details,
    handle_guest_user,
    clear_guest_migration_action
)

User = get_user_model()


class CreateDefaultBoardPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.strategy = Mock()

    def test_create_default_board_pipeline_new_user(self):
        """Test creating a default board for a new user via pipeline."""
        self.strategy.request.session.get.return_value = None
        create_default_board_pipeline(
            strategy=self.strategy,
            user=self.user,
            is_new=True
        )
        self.assertEqual(Board.objects.filter(user=self.user).count(), 1)

    def test_create_default_board_pipeline_existing_user(self):
        """
        Test that no board is created for existing users.
        """
        self.strategy.request.session.get.return_value = None
        create_default_board_pipeline(
            strategy=self.strategy,
            user=self.user,
            is_new=False
        )
        self.assertEqual(Board.objects.filter(user=self.user).count(), 0)

    def test_create_default_board_pipeline_with_merge_action(self):
        """
        Test that no board is created when guest migration action is merge.
        """
        self.strategy.request.session.get.return_value = 'merge'
        create_default_board_pipeline(
            strategy=self.strategy,
            user=self.user,
            is_new=True
        )
        self.assertEqual(Board.objects.filter(user=self.user).count(), 0)


class SyncUserDetailsPipelineTests(TestCase):
    def test_sync_user_details_google_oauth2(self):
        """Test syncing user details from Google OAuth2 response."""
        user = User.objects.create_user(username='testuser')
        response = {
            'given_name': 'John',
            'family_name': 'Doe',
            'email': 'john.doe@example.com',
            'picture': 'http://example.com/avatar.jpg'
        }
        backend = type('Backend', (), {'name': 'google-oauth2'})()
        sync_user_details(
            backend=backend,
            user=user,
            response=response
        )
        user.refresh_from_db()
        self.assertEqual(user.first_name, response['given_name'])
        self.assertEqual(user.last_name, response['family_name'])
        self.assertEqual(user.email, response['email'])
        self.assertEqual(user.avatar_url, response['picture'])


class HandleGuestUserTests(TestCase):
    def setUp(self):
        self.registered_user = User.objects.create_user(
            username='registered_user',
            email='registered@example.com'
        )
        self.guest_user = User.objects.create_user(
            username='guest_user',
            email='guest@example.com',
            is_guest=True
        )
        self.strategy = Mock()
        self.backend = Mock()

    def test_handle_guest_user_merge_action(self):
        """Test merging guest user data when action is 'merge'."""
        Board.objects.create(user=self.guest_user, title="Guest Board")
        Board.objects.create(
            user=self.registered_user, title="Registered Board")
        self.strategy.request.session.get.side_effect = lambda key: {
            'guest_migration_action': 'merge',
            'guest_user_id': str(self.guest_user.id)
        }.get(key)

        handle_guest_user(
            strategy=self.strategy,
            backend=self.backend,
            user=self.registered_user
        )
        self.assertEqual(
            Board.objects.filter(user=self.registered_user).count(), 2)
        self.assertFalse(
            User.objects.filter(id=str(self.guest_user.id)).exists())

    def test_handle_guest_user_discard_action(self):
        """Test discarding guest user when action is 'discard'."""
        self.strategy.request.session.get.side_effect = lambda key: {
            'guest_migration_action': 'discard',
            'guest_user_id': str(self.guest_user.id)
        }.get(key)

        handle_guest_user(
            strategy=self.strategy,
            backend=self.backend,
            user=self.registered_user
        )

        self.assertFalse(User.objects.filter(
            id=str(self.guest_user.id)).exists())

    def test_handle_guest_user_no_action(self):
        """Test that nothing happens when no action is set."""
        self.strategy.request.session.get.return_value = None

        handle_guest_user(
            strategy=self.strategy,
            backend=self.backend,
            user=self.registered_user
        )

        self.assertTrue(User.objects.filter(
            id=str(self.guest_user.id)).exists())

    def test_handle_guest_user_no_guest_user_id(self):
        """
        Test that nothing happens when guest_user_id is absent from session.
        """
        self.strategy.request.session = {
            'guest_migration_action': 'merge'
        }

        with patch('user.pipeline.merge_guest_user') as mock_merge:
            handle_guest_user(
                strategy=self.strategy,
                backend=self.backend,
                user=self.registered_user
            )
            self.assertFalse(mock_merge.called)

    def test_handle_guest_user_non_guest_user(self):
        """Test that nothing happens when user is not a guest user."""
        regular_user = User.objects.create_user(
            username='regular_user',
            is_guest=False
        )
        self.strategy.request.session.get.side_effect = lambda key: {
            'guest_migration_action': 'merge',
            'guest_user_id': str(regular_user.id)
        }.get(key)

        handle_guest_user(
            strategy=self.strategy,
            backend=self.backend,
            user=self.registered_user
        )

        self.assertTrue(User.objects.filter(id=str(regular_user.id)).exists())


class ClearGuestMigrationActionTests(TestCase):
    def setUp(self):
        self.strategy = Mock()
        self.strategy.request.session = {'guest_migration_action': 'merge'}

    def test_clear_guest_migration_action_removes_action(self):
        """
        Test that clear_guest_migration_action removes the action from
        session.
        """
        clear_guest_migration_action(strategy=self.strategy)
        self.assertNotIn(
            'guest_migration_action', self.strategy.request.session)

    def test_clear_guest_migration_action_no_action_in_session(self):
        """Test that function handles case when no action is in session."""
        strategy = Mock()
        strategy.request.session = {}
        clear_guest_migration_action(strategy=strategy)
        self.assertEqual(len(strategy.request.session), 0)

    def test_clear_guest_migration_action_preserves_other_session_data(self):
        """Test that function only removes guest_migration_action."""
        strategy = Mock()
        strategy.request.session = {
            'guest_migration_action': 'merge',
            'other_data': 'should_remain'
        }
        clear_guest_migration_action(strategy=strategy)

        self.assertNotIn('guest_migration_action', strategy.request.session)
        self.assertIn('other_data', strategy.request.session)
        self.assertEqual(
            strategy.request.session['other_data'], 'should_remain')
