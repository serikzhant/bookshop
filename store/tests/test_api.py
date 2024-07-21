import json

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Avg, Case, Count, F, When
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.test.utils import CaptureQueriesContext

from store.models import Book, UserBookRelation
from store.serializers import BooksSerializer


class BooksApiTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='test_username')
        self.book_1 = Book.objects.create(name='Test Book 1', price='25', author_name='Author 1', owner=self.user)
        self.book_2 = Book.objects.create(name='Test Book 2', price='55', author_name='Author 2', owner=self.user)
        self.book_3 = Book.objects.create(name='Test Book 3 Author 1', price='55', author_name='Author 2',
                                          owner=self.user)
        UserBookRelation.objects.create(user=self.user, book=self.book_1, like=True, rate=5)

    def test_get(self):
        url = reverse('book-list')
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
            self.assertEqual(2, len(queries))
        books = Book.objects.all().annotate(
            annotated_likes=Count(Case(When(userbookrelation__like=True, then=1))),
            owner_name=F('owner__username')
        ).order_by('id')
        serializer_data = BooksSerializer(books, many=True).data
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(serializer_data, response.data)
        self.assertEqual(serializer_data[0]['rating'], '5.00')
        self.assertEqual(serializer_data[0]['annotated_likes'], 1)

    def test_get_filter(self):
        url = reverse('book-list')
        books = Book.objects.filter(id__in=[self.book_2.id, self.book_3.id]).annotate(
            annotated_likes=Count(Case(When(userbookrelation__like=True, then=1))),
            owner_name=F('owner__username')
        ).order_by('id')
        response = self.client.get(url, data={'price': 55})
        serializer_data = BooksSerializer(books, many=True).data
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(serializer_data, response.data)

    def test_get_search(self):
        url = reverse('book-list')
        response = self.client.get(url, data={'search': "Author 1"})
        books = Book.objects.filter(id__in=[self.book_1.id, self.book_3.id]).annotate(
            annotated_likes=Count(Case(When(userbookrelation__like=True, then=1))),
            owner_name=F('owner__username')
        ).order_by('id')
        serializer_data = BooksSerializer(books, many=True).data
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(serializer_data, response.data)

    def test_get_sort(self):
        url = reverse('book-list')
        response = self.client.get(url, data={'ordering': "price"})
        books = Book.objects.order_by('price').annotate(
            annotated_likes=Count(Case(When(userbookrelation__like=True, then=1))),
            owner_name=F('owner__username')
        )
        serializer_data = BooksSerializer(books, many=True).data
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(serializer_data, response.data)

    def test_create(self):
        self.assertEqual(3, Book.objects.all().count())
        url = reverse('book-list')
        data = {
            "name": "Python 3",
            "price": "150.00",
            "author_name": "Mark Summerfield"
        }
        json_data = json.dumps(data)
        self.client.force_login(self.user)
        response = self.client.post(url, data=json_data,
                                    content_type='application/json')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(4, Book.objects.all().count())
        self.assertEqual(self.user, Book.objects.last().owner)

    def test_update(self):
        url = reverse('book-detail', args=(self.book_1.id,))
        data = {
            "name": self.book_1.name,
            "price": 505,
            "author_name": self.book_1.author_name
        }
        json_data = json.dumps(data)
        self.client.force_login(self.user)
        response = self.client.put(url, data=json_data,
                                   content_type='application/json')
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.book_1.refresh_from_db()
        self.assertEqual(505, self.book_1.price)

    def test_get_one(self):
        url = reverse('book-detail', args=(self.book_2.id,))
        response = self.client.get(url)
        data = {
            'id': self.book_2.id,
            'name': self.book_2.name,
            'price': self.book_2.price + '.00',
            'author_name': self.book_2.author_name,
            'annotated_likes': 0,
            'rating': None,
            'owner_name': 'test_username',
            'readers': []
        }
        self.assertEqual(data, response.data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_delete(self):
        self.assertEqual(3, Book.objects.all().count())
        self.client.force_login(self.user)
        url = reverse('book-detail', args=(self.book_2.id,))
        response = self.client.delete(url)
        self.assertEqual(2, Book.objects.all().count())
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_update_not_owner(self):
        self.user2 = User.objects.create(username='test_username2')
        url = reverse('book-detail', args=(self.book_1.id,))
        data = {
            "name": self.book_1.name,
            "price": 505,
            "author_name": self.book_1.author_name
        }
        json_data = json.dumps(data)
        self.client.force_login(self.user2)
        response = self.client.put(url, data=json_data,
                                   content_type='application/json')
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.book_1.refresh_from_db()
        self.assertEqual(25, self.book_1.price)

    def test_update_not_owner_but_staff(self):
        self.user2 = User.objects.create(username='test_username2', is_staff=True)
        url = reverse('book-detail', args=(self.book_1.id,))
        data = {
            "name": self.book_1.name,
            "price": 505,
            "author_name": self.book_1.author_name
        }
        json_data = json.dumps(data)
        self.client.force_login(self.user2)
        response = self.client.put(url, data=json_data,
                                   content_type='application/json')
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.book_1.refresh_from_db()
        self.assertEqual(505, self.book_1.price)


class BooksRelationTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='test_username')
        self.user2 = User.objects.create(username='test_username2')
        self.book_1 = Book.objects.create(name='Test Book 1', price='25', author_name='Author 1', owner=self.user)
        self.book_2 = Book.objects.create(name='Test Book 2', price='55', author_name='Author 2', owner=self.user)

    def test_like(self):
        url = reverse('userbookrelation-detail', args=(self.book_1.id,))
        self.client.force_login(self.user)
        data = {
            "like": True,
        }
        json_data = json.dumps(data)
        response = self.client.patch(url, data=json_data,
                                     content_type='application/json')
        relation = UserBookRelation.objects.get(user=self.user, book=self.book_1)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertTrue(relation.like)

        data = {
            "in_bookmarks": True,
        }
        json_data = json.dumps(data)
        response = self.client.patch(url, data=json_data,
                                     content_type='application/json')
        relation = UserBookRelation.objects.get(user=self.user, book=self.book_1)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertTrue(relation.in_bookmarks)

    def test_rate(self):
        url = reverse('userbookrelation-detail', args=(self.book_1.id,))
        self.client.force_login(self.user)
        data = {
            "rate": 3,
        }
        json_data = json.dumps(data)
        response = self.client.patch(url, data=json_data,
                                     content_type='application/json')
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        relation = UserBookRelation.objects.get(user=self.user, book=self.book_1)
        self.assertEqual(3, relation.rate)

    def test_rate_wrong(self):
        url = reverse('userbookrelation-detail', args=(self.book_1.id,))
        self.client.force_login(self.user)
        data = {
            "rate": 6,
        }
        json_data = json.dumps(data)
        response = self.client.patch(url, data=json_data,
                                     content_type='application/json')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
