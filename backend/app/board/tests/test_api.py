import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from board.models import Board, Column

User = get_user_model()
BOARD_URL = reverse('api:boards')
LATEST_BOARD_URL = reverse('api:latest-board')


def board_detail_url(board_id: int) -> str:
    """Return the detail URL for a board."""
    return reverse('api:board-detail', args=[str(board_id)])


def column_url(board_id: int) -> str:
    return reverse('api:columns', args=[board_id])


def column_detail_url(board_id: int, column_id: int) -> str:
    return reverse('api:column-detail', args=[board_id, column_id])


def column_move_before_url(board_id: int, column_id: int) -> str:
    """Return the URL to move a column before another column."""
    return reverse('api:column-move-before', args=[board_id, column_id])


def column_move_end_url(board_id: int, column_id: int) -> str:
    """Return the URL to move a column to the end of its board."""
    return reverse('api:column-move-end', args=[board_id, column_id])


class PrivateBoardsApiTests(TestCase):
    """Test authenticated requests to the boards API."""

    def setUp(self):
        self.user = User.objects.create_user('testuser@example.com')
        self.client = Client()
        self.client.force_login(self.user)

    def test_retrieve_boards(self):
        """Test retrieving a list of boards."""
        board1 = Board.objects.create(title='b1', user=self.user)
        board2 = Board.objects.create(title='b2', user=self.user)
        another_user = User.objects.create_user('anotheruser@example.com')
        Board.objects.create(title='b3', user=another_user)
        res = self.client.get(BOARD_URL)
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(content), 2)

        expected_boards = {str(board1.id): board1, str(board2.id): board2}

        for board_data in content:
            board_id = str(board_data['id'])
            self.assertIn(board_id, expected_boards)

            expected_board = expected_boards[board_id]
            self.assertEqual(board_data['title'], expected_board.title)
            self.assertEqual(board_data['starred'], expected_board.starred)
            self.assertIn('updated_at', board_data)

    def test_create_board(self):
        """Test creating a new board with columns."""
        payload = {
            'title': 'New Board',
            'columns': ['To Do', 'In Progress', 'Done']
        }
        res = self.client.post(
            BOARD_URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 201)
        board = Board.objects.get(user=self.user, title=payload['title'])
        created_columns = set(
            Column.objects.filter(board=board).values_list('title', flat=True)
        )
        self.assertEqual(created_columns, set(payload['columns']))

    def test_create_board_duplicate_title_allowed(self):
        """Test creating a board with a duplicate title is now allowed."""
        Board.objects.create(user=self.user, title='Duplicate Title')
        payload = {'title': 'Duplicate Title', 'columns': ['To Do']}
        res = self.client.post(
            BOARD_URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 201)
        duplicate_boards = Board.objects.filter(
            user=self.user, title='Duplicate Title')
        self.assertEqual(duplicate_boards.count(), 2)

    def test_retrieve_board(self):
        """Test retrieving a board."""
        board = Board.objects.create(user=self.user, title='A Board')
        Column.objects.create(board=board, title='To Do')
        Column.objects.create(board=board, title='Done')
        url = board_detail_url(str(board.id))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(str(content['id']), str(board.id))
        self.assertEqual(content['title'], board.title)
        column_titles = {col['title'] for col in content['columns']}
        self.assertEqual(column_titles, {'To Do', 'Done'})
        self.assertIn('created_at', content)
        self.assertIn('updated_at', content)
        self.assertIn('starred', content)

    def test_retrieve_latest_updated_board(self):
        """Test retrieving the latest updated board."""
        Board.objects.create(
            user=self.user, title='A Board')
        latest_updated_board = Board.objects.create(
            user=self.user, title='Another Board')
        Board.objects.create(
            user=self.user, title='Board 3')
        latest_updated_board.title = 'Board Updated'
        latest_updated_board.save()

        res = self.client.get(LATEST_BOARD_URL)
        self.assertEqual(res.status_code, 200)
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(str(content['id']), str(latest_updated_board.id))
        self.assertEqual(content['title'], latest_updated_board.title)

    def test_retrieve_latest_updated_board_no_boards(self):
        """Test retrieving the latest updated board when no boards exist."""
        res = self.client.get(LATEST_BOARD_URL)
        self.assertEqual(res.status_code, 404)

    def test_update_board(self):
        """Test updating a board."""
        board = Board.objects.create(user=self.user, title='A Board')
        url = board_detail_url(str(board.id))
        payload = {'title': 'Updated Board'}
        res = self.client.patch(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        board.refresh_from_db()
        self.assertEqual(board.title, payload['title'])

    def test_update_board_starred(self):
        """Test updating the starred field of a board."""
        board = Board.objects.create(
            user=self.user, title='A Board', starred=False)
        url = board_detail_url(str(board.id))
        payload = {'starred': True}
        res = self.client.patch(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        board.refresh_from_db()
        self.assertTrue(board.starred)

    def test_delete_board(self):
        """Test deleting a board."""
        board = Board.objects.create(user=self.user, title='A Board')
        url = board_detail_url(str(board.id))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        exists = Board.objects.filter(id=str(board.id)).exists()
        self.assertFalse(exists)

    def test_add_column_to_board(self):
        """Test adding a column to an existing board."""
        board = Board.objects.create(user=self.user, title='A Board')
        col1 = Column.objects.create(board=board, title='To Do')
        col2 = Column.objects.create(board=board, title='In Progress')
        payload = {
            'title': 'Done'
        }
        res = self.client.post(
            column_url(str(board.id)),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        all_columns = Column.objects.filter(board=board)
        self.assertEqual(
            list(all_columns.values_list('title', flat=True)),
            [col1.title, col2.title, payload['title']]
        )

    def test_delete_column_from_board(self):
        """Test deleting a column from a board."""
        board = Board.objects.create(user=self.user, title='A Board')
        col1 = Column.objects.create(board=board, title='To Do')
        col2 = Column.objects.create(board=board, title='In Progress')
        col3 = Column.objects.create(board=board, title='Done')

        res = self.client.delete(
            column_detail_url(str(board.id), str(col2.id))
        )
        self.assertEqual(res.status_code, 204)

        remaining_columns = Column.objects.filter(board=board)
        self.assertEqual(list(remaining_columns), [col1, col3])

    def test_update_column_from_board(self):
        """Test updating a column from a board."""
        board = Board.objects.create(user=self.user, title='A Board')
        column = Column.objects.create(board=board, title='To Do')

        payload = {
            'title': 'Updated To Do'
        }
        url = column_detail_url(str(board.id), str(column.id))
        res = self.client.patch(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)

        column.refresh_from_db()
        self.assertEqual(column.title, payload['title'])

    def test_move_column_before(self):
        """Test moving a column before another column."""
        board = Board.objects.create(user=self.user, title='A Board')
        column1 = Column.objects.create(board=board, title='Column 1')
        column2 = Column.objects.create(board=board, title='Column 2')
        url = column_move_before_url(str(board.id), str(column2.id))
        payload = {'target_column_id': str(column1.id)}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        column1.refresh_from_db()
        column2.refresh_from_db()
        self.assertLess(column2.order, column1.order)

    def test_move_column_before_different_board(self):
        """
        Test that moving a column before another column in a different board
        fails.
        """
        board = Board.objects.create(user=self.user, title='A Board')
        another_board = Board.objects.create(
            user=self.user, title='Another Board')
        column1 = Column.objects.create(board=board, title='Column 1')
        column2 = Column.objects.create(board=another_board, title='Column 2')
        column1_order = column1.order
        column2_order = column2.order
        url = column_move_before_url(str(another_board.id), str(column2.id))
        payload = {'target_column_id': str(column1.id)}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)
        column1.refresh_from_db()
        column2.refresh_from_db()
        self.assertEqual(column1.order, column1_order)
        self.assertEqual(column2.order, column2_order)

    def test_move_column_before_not_found(self):
        """
        Test that moving a non-existent column before another returns 404.
        """
        board = Board.objects.create(user=self.user, title='A Board')
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = column_move_before_url(str(board.id), non_existent_id)
        payload = {'target_column_id': non_existent_id}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)

    def test_move_column_to_end(self):
        """Test moving a column to the end of its board."""
        board = Board.objects.create(user=self.user, title='A Board')
        column1 = Column.objects.create(board=board, title='Column 1')
        column2 = Column.objects.create(board=board, title='Column 2')
        column3 = Column.objects.create(board=board, title='Column 3')
        url = column_move_end_url(str(board.id), str(column1.id))
        res = self.client.post(
            url,
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        column1.refresh_from_db()
        column2.refresh_from_db()
        column3.refresh_from_db()
        self.assertGreater(column1.order, column2.order)
        self.assertGreater(column1.order, column3.order)

    def test_move_column_to_end_not_found(self):
        """Test that moving a non-existent column to end returns 404."""
        board = Board.objects.create(user=self.user, title='A Board')
        non_existent_id = '00000000-0000-0000-0000-000000000000'
        url = column_move_end_url(str(board.id), non_existent_id)
        res = self.client.post(url, content_type='application/json')
        self.assertEqual(res.status_code, 404)
