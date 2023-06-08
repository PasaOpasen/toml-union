
build:
	docker build --target toml_union -t toml-union "."

run:
	docker run -it --rm toml-union

