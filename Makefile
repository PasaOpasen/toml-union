
VERSION=$(shell cat version.txt)

help:
	venv/bin/python ./toml_union/toml_union.py -h


build:
	docker build --target toml_union -t toml-union "."

run:
	docker run -it --rm toml-union

push:
	docker tag toml-union pasaopasen/toml-union:latest
	docker push pasaopasen/toml-union:latest
	docker tag toml-union pasaopasen/toml-union:$(VERSION)
	docker push pasaopasen/toml-union:$(VERSION)

docker-test:
	cd examples; bash docker-test.sh

doctest:
	venv/bin/python -m pytest --doctest-modules ./toml_union/toml_union.py

pytest:
	venv/bin/python -m pytest ./tests

autotest: doctest pytest



