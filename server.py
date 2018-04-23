#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from bson import errors as bson_errors
from bson import json_util, objectid
from flask import Flask, Response, request
from pymongo import MongoClient

import config
import errors


app = Flask(__name__)
app.config.from_object(config.main_config)

if os.environ.get('SONG_API_CONFIG'):
    app.config.from_envvar('SONG_API_CONFIG')

client = MongoClient()
collection = client[app.config['MONGO_DB']]['songs']

@app.route("/songs", methods=['GET'])
def get_songs():
    """GET /songs returns a list of songs with with their associated details. 
    Pagination is possible by using the 'n' and 'p' parameters. Note that a 'p'
    value beyond the end of the number of items in the collection will return 
    an empty array.

    Params:
        int p: the page number of results to display (0 indexed)
        int n: the number of items to show on a page (default: 10)
    """
    args = {
        'p': request.args.get('p') or 0,
        'n': request.args.get('n') or 10
    }

    # Validate args
    for arg, val in args.items():
        if val:
            try:
                args[arg] = int(val)
                if args[arg] < 0:
                    raise ValueError
            except ValueError:
                e = errors.InvalidArgumentError(val, arg)
                return Response(
                    json_util.dumps(e.to_dict()),
                    mimetype='application/json',
                    status=e.status_code
                )

    limit = args['n']
    skip = args['p'] * limit

    return Response(
        json_util.dumps(collection.find(skip=skip, limit=limit)),
        mimetype='application/json'
    )

@app.route("/songs/avg/difficulty", methods=['GET'])
def get_avg_difficulty():
    """GET /songs/avg/difficulty returns the average difficulty for all songs. 

    Params:
        int level: limits results to songs from a specified level
    """
    pipeline = [
        {
            "$group": {
                "_id": "$level",
                "averageDifficulty": {"$avg": "$difficulty"}
            }
        }
    ]

    level = request.args.get('level')
    if level:
        try:
            level = int(level)
            pipeline.append({
                "$match": {
                    "_id": level
                }
            })
        except ValueError:
            e = errors.InvalidArgumentError(level, 'level')
            return Response(
                json_util.dumps(e.to_dict()),
                mimetype='application/json',
                status=e.status_code
            )
    return Response(
        json_util.dumps(collection.aggregate(pipeline)),
        mimetype='application/json'
    )

@app.route("/songs/search", methods=['GET'])
def songs_search():
    """GET /songs/search performs a full-text search against the song collection's 
    'artist' and 'title' fields. Omitting the 'message' parameter will raise a 
    MissingRequireArgumentError exception.

    Params:
        string message (required): the case-insensitive, unicode-safe query string
    """
    message = request.args.get('message')
    if not message:
        e = errors.MissingRequireArgumentError('message', request.path)
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    q = collection.find({"$text": {"$search": message}})

    return Response(
        json_util.dumps(q),
        mimetype='application/json'
    )

@app.route("/songs/rating", methods=['POST'])
def songs_rating():
    """POST /songs/rating adds a numeric rating (1-5, inclusive) to a song.

    Params:
        string song_id (required): the song's MongoDB ObjectID
        int rating (required): the rating to be assigned to the song (1-5)
    """
    song_id = request.form.get('song_id')
    if not song_id:
        e = errors.MissingRequireArgumentError('song_id', request.path)
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    try:
        song_id = objectid.ObjectId(song_id)
    except bson_errors.InvalidId:
        e = errors.InvalidArgumentError(song_id, 'song_id')
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    rating = request.form.get('rating')

    if not rating or rating not in ('1', '2', '3', '4', '5'):
        e = errors.InvalidArgumentError(rating, 'rating')
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    result = collection.update_one(
        {"_id": song_id},
        {"$inc": {"rating.{}".format(rating): 1}}
    )

    if not result.matched_count:
        e = errors.ObjectNotFoundError(song_id)
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    return Response(
        json_util.dumps({'status': 'OK'}),
        status=200,
        mimetype='application/json'
    )

@app.route("/songs/avg/rating/<song_id>", methods=['GET'])
def songs_ratings(song_id):
    """GET /songs/avg/rating/<song_id> gets a song's min, max, and average ratings.

    Params:
        string song_id (required): the song's MongoDB ObjectID
    """
    try:
        song_id = objectid.ObjectId(song_id)
    except bson_errors.InvalidId:
        e = errors.InvalidArgumentError(song_id, 'song_id')
        return Response(
            json_util.dumps(e.to_dict()),
            mimetype='application/json',
            status=e.status_code
        )

    song = collection.find_one({"_id": song_id})
    ratings = song ['rating']
    min_rating = min([int(i) for i in ratings.keys()])
    max_rating = max([int(i) for i in ratings.keys()])
    accu, count = 0, 0
    for k, v in ratings.items():
        count += v
        accu += float(k) * v

    avg_rating = accu / count
    d = {
        '_id': song['_id'],
        'min_rating': min_rating,
        'max_rating': max_rating,
        'avg_rating': avg_rating
    }

    return Response(
        json_util.dumps(d),
        mimetype='application/json'
    )


if __name__ == "__main__":
    app.run(host='0.0.0.0')
