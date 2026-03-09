import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from board.models import Board, Column
from card.models import Card


User = get_user_model()
CARDS_URL = reverse('api:cards')


def card_detail_url(card_id) -> str:
    """Return the detail URL for a card."""
    return reverse('api:card-detail', args=[str(card_id)])


def card_move_above_url(card_id) -> str:
    """Return the URL to move a card above another card."""
    return reverse('api:card-move-above', args=[str(card_id)])


def card_move_bottom_url(card_id) -> str:
    """Return the URL to move a card to the bottom of its column."""
    return reverse('api:card-move-bottom', args=[str(card_id)])


class PrivateCardsApiTests(TestCase):
    """Test authenticated requests to the cards API."""

    def setUp(self):
        self.user = User.objects.create_user('testuser@example.com')
        self.client = Client()
        self.client.force_login(self.user)

        self.board = Board.objects.create(title='Test Board', user=self.user)
        self.column = Column.objects.create(board=self.board, title='To Do')

    def test_list_cards(self):
        """Test retrieving a list of cards."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(title='Card 2', column=self.column)
        Card.objects.create(title='Card 3', column=another_column)
        res = self.client.get(CARDS_URL)
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(res.status_code, 200)
        expected = [
            {'id': str(c.id), 'title': c.title, 'priority': c.priority.value}
            for c in (card1, card2)
        ]
        self.assertEqual(content, expected)

    def test_filter_cards_by_column(self):
        """Test filtering cards by column."""
        another_column = Column.objects.create(board=self.board, title='Done')
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(title='Card 2', column=self.column)
        Card.objects.create(title='Card 3', column=another_column)
        res = self.client.get(CARDS_URL, {'column_id': self.column.id})
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(res.status_code, 200)
        expected = [
            {'id': str(c.id), 'title': c.title, 'priority': c.priority.value}
            for c in (card1, card2)
        ]
        self.assertEqual(content, expected)

    def test_create_card_successful(self):
        """Test creating a new card."""
        payload = {
            'title': 'New Card',
            'body': 'Card body content',
            'priority': 'high',
            'column_id': str(self.column.id)
        }
        res = self.client.post(
            CARDS_URL,
            payload,
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 201)
        card = Card.objects.get(id=str(res.json()['id']))
        for key in payload:
            if key == 'column_id':
                self.assertEqual(str(card.column.id), str(self.column.id))
            else:
                self.assertEqual(getattr(card, key), payload[key])

    def test_retrieve_card(self):
        """Test retrieving a single card."""
        card = Card.objects.create(
            title='A Card', body='A Body', column=self.column)
        url = card_detail_url(card.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = json.loads(res.content.decode('utf-8'))
        self.assertEqual(str(content['id']), str(card.id))
        self.assertEqual(content['title'], card.title)
        self.assertEqual(content['body'], card.body)
        self.assertEqual(content['priority'], card.priority.value)
        self.assertEqual(str(content['column_id']), str(card.column.id))
        self.assertEqual(str(content['board_id']), str(card.column.board.id))

    def test_retrieve_card_not_owned(self):
        """Test that retrieving a card not owned by the user fails."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card = Card.objects.create(
            title='Another Card', body='Another Body', column=another_column)
        url = card_detail_url(card.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_update_card(self):
        """Test updating a card."""
        card = Card.objects.create(
            title='Old Title', body='Old Body', column=self.column)
        another_column = Column.objects.create(board=self.board, title='Done')
        url = card_detail_url(str(card.id))
        payload = {
            'title': 'Updated Title',
            'body': 'Updated Body',
            'priority': 'low',
            'column_id': str(another_column.id)
        }
        res = self.client.patch(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        card.refresh_from_db()
        self.assertEqual(card.title, payload['title'])
        self.assertEqual(card.body, payload['body'])
        self.assertEqual(card.column.id, another_column.id)
        self.assertEqual(card.priority, payload['priority'])

    def test_card_non_editable_fields_unchanged(self):
        """Test that non-editable fields of a card remain unchanged."""
        card = Card.objects.create(
            title='Initial Title', body='Initial Body', column=self.column)
        url = card_detail_url(card.id)
        payload = {
            'id': 999,
            'created_at': '2020-01-01T00:00:00Z',
            'updated_at': '2020-01-01T00:00:00Z'
        }
        res = self.client.patch(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        card.refresh_from_db()
        self.assertNotEqual(card.id, payload['id'])
        self.assertNotEqual(card.created_at.isoformat(), payload['created_at'])
        self.assertNotEqual(card.updated_at.isoformat(), payload['updated_at'])

    def test_update_card_not_found(self):
        """Test that updating a card not owned by the user returns 404."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card = Card.objects.create(
            title='Another Card', body='Another Body', column=another_column)
        url = card_detail_url(card.id)
        payload = {'title': 'Should Not Update'}
        res = self.client.patch(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)
        card.refresh_from_db()
        self.assertEqual(card.title, 'Another Card')

    def test_delete_card(self):
        """Test deleting a card."""
        card = Card.objects.create(
            title='Card to Delete', body='Body', column=self.column)
        url = card_detail_url(card.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Card.objects.filter(id=card.id).exists())

    def test_delete_card_not_found(self):
        """Test that deleting a card not owned by the user returns 404."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card = Card.objects.create(
            title='Another Card', body='Another Body', column=another_column)
        url = card_detail_url(card.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Card.objects.filter(id=card.id).exists())

    def test_move_card_above(self):
        """Test moving a card above another card."""
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(title='Card 2', column=self.column)
        url = card_move_above_url(card2.id)
        payload = {'target_card_id': str(card1.id)}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        card1.refresh_from_db()
        card2.refresh_from_db()
        self.assertLess(card2.order, card1.order)

    def test_move_card_above_different_column(self):
        """
        Test that moving a card above another card in a different column
        fails.
        """
        another_column = Column.objects.create(board=self.board, title='Done')
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(title='Card 2', column=another_column)
        card1_order = card1.order
        card2_order = card2.order
        url = card_move_above_url(card2.id)
        payload = {'target_card_id': str(card1.id)}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)
        card1.refresh_from_db()
        card2.refresh_from_db()
        self.assertEqual(card1.order, card1_order)
        self.assertEqual(card2.order, card2_order)

    def test_move_card_above_not_found(self):
        """Test that moving a non-existent card above another returns 404."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(
            title='Card 2', column=another_column)
        url = card_move_above_url(card2.id)
        payload = {'target_card_id': str(card1.id)}
        res = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)

    def test_move_card_to_bottom(self):
        """Test moving a card to the bottom of its column."""
        card1 = Card.objects.create(title='Card 1', column=self.column)
        card2 = Card.objects.create(title='Card 2', column=self.column)
        card3 = Card.objects.create(title='Card 3', column=self.column)
        url = card_move_bottom_url(card1.id)
        res = self.client.post(
            url,
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        card1.refresh_from_db()
        card2.refresh_from_db()
        card3.refresh_from_db()
        self.assertGreater(card1.order, card2.order)
        self.assertGreater(card1.order, card3.order)

    def test_move_card_to_bottom_not_found(self):
        """Test that moving a non-existent card to bottom returns 404."""
        another_user = User.objects.create_user('anotheruser@example.com')
        another_board = Board.objects.create(
            title='Another Board', user=another_user)
        another_column = Column.objects.create(
            board=another_board, title='In Progress')
        card = Card.objects.create(
            title='Another Card', column=another_column)
        url = card_move_bottom_url(card.id)
        res = self.client.post(url, content_type='application/json')
        self.assertEqual(res.status_code, 404)
