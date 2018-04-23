#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import unittest

from bson import objectid
from pymongo import MongoClient, TEXT

import config
import errors
import server


class ApiBaseTestCase(unittest.TestCase):

    def setUp(self):
        """Initialize test app"""
        self.app = server.app.test_client()

class ApiMongoTestCase(ApiBaseTestCase):

    def setUp(self):
        """Setup Mongo connection"""
        super().setUp()
        client = MongoClient()
        self.collection = client.api_test.songs
        
    def tearDown(self):
        super().tearDown()
        self.collection.drop()


class ApiEmptyDBTestCase(ApiMongoTestCase):

    def test_get_songs_empty_db(self):
        """
        A GET on /songs with an empty database should return 200 and an empty JSON.
        """
        rv = self.app.get('/songs')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.data, b'[]')

    def test_get_avg_difficulty_empty_db(self):
        """
        A GET on /songs with an empty database should return 200 and an empty JSON.
        """
        rv = self.app.get('/songs/avg/difficulty')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.data, b'[]')

class ApiFixtureDBTestCase(ApiMongoTestCase):

    def setUp(self):
        """Insert test data into db"""
        super().setUp()
        with open('songs.json') as f:
            result = self.collection.insert_many([json.loads(line) for line in f.readlines()])
            self.assertTrue(result.acknowledged)
            self.fixture_ids = result.inserted_ids
            self.collection.create_index([("artist", TEXT), ("title", TEXT)])

    def test_get_songs(self):
        rv = self.app.get('/songs')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 10)

    def test_get_songs_with_n(self):
        rv = self.app.get('/songs?n=3')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 3)
        self.assertEqual(j[2]['artist'], 'Mr Fastfinger')

    def test_get_songs_with_p(self):
        rv = self.app.get('/songs?p=1')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 1)
        self.assertEqual(j[0]['title'], 'Babysitting')

    def test_get_songs_with_n_and_p(self):
        rv = self.app.get('/songs?p=2&n=3')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 3)
        self.assertEqual(j[0]['title'], 'Greasy Fingers - boss level')

    def test_get_songs_with_p_too_big(self):
        rv = self.app.get('/songs?p=3')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 0)
        self.assertEqual(j, [])

    def test_get_songs_with_invalid_n_and_p(self):
        rv = self.app.get('/songs?p=fake')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)

        rv = self.app.get('/songs?n=fake')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)

        rv = self.app.get('/songs?p=fake&n=fake')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)

        rv = self.app.get('/songs?n=-1')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)

    def test_get_avg_difficulty(self):
        rv = self.app.get('/songs/avg/difficulty')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 4)

    def test_get_avg_difficulty_with_level(self):
        rv = self.app.get('/songs/avg/difficulty?level=6')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 1)

    def test_get_avg_difficulty_with_level_not_found(self):
        rv = self.app.get('/songs/avg/difficulty?level=11')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 0)
        self.assertEqual(j, [])

    def test_get_avg_difficulty_with_invalid_level(self):
        rv = self.app.get('/songs/avg/difficulty?level=fake')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"fake" is not a valid argument for parameter "level"')

    def test_songs_search_no_message(self):
        rv = self.app.get('/songs/search')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.MissingRequireArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], 'argument "message" is required for endpoint "/songs/search"')

    def test_songs_search_valid_message(self):
        def _assert_valid_message(rv):
            self.assertEqual(rv.status_code, 200)
            j = json.loads(rv.data)
            self.assertEqual(len(j), 1)
            self.assertEqual(j[0]['artist'], 'Mr Fastfinger')

        # Basic test
        rv = self.app.get('/songs/search?message=Fastfinger')
        _assert_valid_message(rv)

        # Mixed cases
        rv = self.app.get('/songs/search?message=fAsTfInGeR')
        _assert_valid_message(rv)

        # Search on title
        rv = self.app.get('/songs/search?message=Awaki-Waki')
        _assert_valid_message(rv)

    def test_songs_search_valid_message_return_multi(self):
        rv = self.app.get('/songs/search?message=Yousicians')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 10)

    def test_songs_search_valid_message_edge_cases(self):
        # MongoDB $text search ignores stop words such as 'the'
        rv = self.app.get('/songs/search?message=the')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 0)

        # MongoDB $text search ignores diacritics by default
        rv = self.app.get('/songs/search?message=gréåsy')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 1)
        self.assertEqual(j[0]['title'], 'Greasy Fingers - boss level')

        # Spaces in the message are okay
        rv = self.app.get('/songs/search?message=greasy fingers')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(len(j), 1)
        self.assertEqual(j[0]['title'], 'Greasy Fingers - boss level')

    def test_songs_rating_null_body(self):
        rv = self.app.post('/songs/rating')
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.MissingRequireArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], 'argument "song_id" is required for endpoint "/songs/rating"')

    def test_songs_rating_invalid_id(self):
        rv = self.app.post('/songs/rating', data={'song_id': 'hdhhd'})
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"hdhhd" is not a valid argument for parameter "song_id"')

    def test_songs_rating_invalid_rating(self):
        # Missing 'rating' param should throw an error
        rv = self.app.post('/songs/rating', data={'song_id': objectid.ObjectId()})
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"None" is not a valid argument for parameter "rating"')

        # Invalid 'rating' param should throw an error
        rv = self.app.post('/songs/rating', data={'song_id': objectid.ObjectId(), 'rating': 'invalid'})
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"invalid" is not a valid argument for parameter "rating"')

        # Out of bounds 'rating' param should throw an error
        rv = self.app.post('/songs/rating', data={'song_id': objectid.ObjectId(), 'rating': 10})
        self.assertEqual(rv.status_code, 500)
        self.assertRaises(errors.InvalidArgumentError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"10" is not a valid argument for parameter "rating"')

    def test_songs_rating_not_found(self):
        oid = objectid.ObjectId()
        rv = self.app.post('/songs/rating', data={'song_id': oid, 'rating': 4})
        self.assertEqual(rv.status_code, 404)
        self.assertRaises(errors.ObjectNotFoundError)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], 'song_id "{}" not found'.format(oid))

    def test_songs_rating_success(self):
        oid = self.fixture_ids[0]
        rv = self.app.post('/songs/rating', data={'song_id': oid, 'rating': 4})
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(j['status'], 'OK')

        # Assert that rating was in fact incremented correctly
        rv = self.app.get('/songs')
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        
        self.assertEqual(j[0]['rating'], {'4': 1})

    def test_songs_avg_rating_success(self):
        oid = self.fixture_ids[0]
        rv = self.app.post('/songs/rating', data={'song_id': oid, 'rating': 4})
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        self.assertEqual(j['status'], 'OK')

        # Assert that rating was in fact incremented correctly
        rv = self.app.get('/songs/avg/rating/{}'.format(oid))
        self.assertEqual(rv.status_code, 200)
        j = json.loads(rv.data)
        
        self.assertEqual(j['min_rating'], 4)
        self.assertEqual(j['max_rating'], 4)
        self.assertEqual(j['avg_rating'], 4)

    def test_songs_avg_rating_invalid_oid(self):
        oid = 'fake'
        rv = self.app.get('/songs/avg/rating/{}'.format(oid))
        self.assertEqual(rv.status_code, 500)
        j = json.loads(rv.data)
        self.assertEqual(j['message'], '"fake" is not a valid argument for parameter "song_id"')


if __name__ == '__main__':
    unittest.main()