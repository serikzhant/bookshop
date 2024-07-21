from unittest import TestCase

from django.contrib.auth.models import User

from store.logic import set_rating
from store.models import Book, UserBookRelation


class SetRatingTestCase(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user11', first_name='Ian', last_name='Hose')
        user2 = User.objects.create(username='user12', first_name='Sam', last_name='Smith')
        user3 = User.objects.create(username='user13', first_name='Max', last_name='Mad')

        # user1 = User.objects.get(username='user11')
        # user2 = User.objects.get(username='user12')
        # user3 = User.objects.get(username='user13')
    #
        self.book_1 = Book.objects.create(name='Test Book 1', price='25', author_name='Author 1', owner=user1)
    #
        UserBookRelation.objects.create(user=user1, book=self.book_1, like=True, rate=5)
        UserBookRelation.objects.create(user=user2, book=self.book_1, like=True, rate=5)
        UserBookRelation.objects.create(user=user3, book=self.book_1, like=True, rate=4)

    def test_ok(self):
        set_rating(self.book_1)
        self.book_1.refresh_from_db()
        self.assertEqual(str(self.book_1.rating), '4.67')
