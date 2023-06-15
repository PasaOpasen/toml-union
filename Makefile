
build:
	docker build --target toml_union -t toml-union "."

run:
	docker run -it --rm toml-union

push:
	docker tag toml-union pasaopasen/toml-union:latest
	docker push pasaopasen/toml-union:latest
	docker tag toml-union pasaopasen/toml-union:1
	docker push pasaopasen/toml-union:1

test:
	cd examples; bash docker-test.sh
