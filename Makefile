.PHONY: init-venv install-requirements test coverage run-server init-mongo setup all

all: setup init-mongo test run-server

init-venv:
	python3 -m venv --clear ./venv

install-requirements:
	. venv/bin/activate && \
	pip install -r requirements.txt

test:
	. venv/bin/activate && \
	SONG_API_CONFIG="config/test_config.py" python3 server_test.py

coverage:
	. venv/bin/activate && \
	SONG_API_CONFIG="config/test_config.py" coverage run --omit="venv/*" server_test.py && \
	coverage html

run-server:
	mongod --dbpath data &
	. venv/bin/activate && \
	python3 server.py

init-mongo:
	mongoimport --db api --collection songs --drop --file songs.json
	mongo init.js

setup: init-venv install-requirements
