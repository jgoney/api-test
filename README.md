# api-test

## Prerequisites

 - Python 3.x
 - MongoDB 3.x
 - A Unix-based system if you'd like to use the Makefile commands

## Getting started

Quickstart:
 ```bash
 make  # runs setup, runs the tests, and starts the server
  ```

 To setup the virtualenv and install requirements:
 ```bash
 make setup
  ```

 To populate the db and create indices:
 ```bash
 make init-mongo
  ```

To start the server:
 ```bash
 make run-server
  ```

To run tests:
 ```bash
 make test  # runs tests
 make coverage  # runs tests with coverage report
  ```

## Using the API

Refer to the docstrings in [server.py](server.py) for more info on using each endpoint.
