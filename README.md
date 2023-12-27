
- [About](#about)
  - [Python usage example](#python-usage-example)
  - [Overrides](#overrides)
  - [CLI](#cli)


# About

This script combines several `*.toml` files (usially `pyproject.toml`) into one. If it finds some conflict between items, they are kept for manual review.

It has a docker image (`docker pull pasaopasen/toml-union`) and an [example](/examples/docker-test.sh) of its usage.

## Python usage example

```python
from pathlib import Path

from toml_union import toml_union_process

# run union
toml_union_process(
    files=Path('input').glob('*.toml'),   # get all *.toml files from examples dir
    outfile='output.toml',  # set output file path
    report='report.json',   # path for conflicts report on conflict case
)

```

It combines next files:

```toml
[tool.poetry]
name = "project 1"
version = "1.6.0"
description = "Some words"
authors = ["Me"]

[tool.poetry.dependencies]
"pdfminer.six" = "^20220524"
cmake = "^3.21.1"
other_package = "1"

[tool.poetry.group.dev.dependencies]
autopep8 = "^1.5"
black = "~21.8b0"
ipython = "^8.0"
pylint-django = "^2.3.0"
pytest-django = "^4.5.2"
```

```toml
[tool.poetry]
name = "project 2"
version = "1.6.0"
description = "Some words"
authors = ["Me"]

[tool.poetry.dependencies]
"pdfminer.six" = "^2022333333334"
torch = { version = "1.10.1+cu113", source = "pytorch" }
torchvision = { version = "0.11.2+cu113", source = "pytorch" }
other_package = "2"

[tool.poetry.group.dev.dependencies]
autopep8 = "^1.5"
black = "~21.8b0"
pytest-django = "^4.5.2"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

```toml
[tool.poetry]
name = "project 1"
version = "1.6.0"
description = "Some words"
authors = ["Somebody"]

[tool.poetry.dependencies]
"pdfminer.six" = "^20220524"
ansi2html = "^1.7"
beautifulsoup4 = "^4.10.0"
boto3 = "^1.16.56"
chardet = "^4.0.0"
Django = "~3.1"
django-allauth = "^0.51"
django-rosetta = "^0.9.5"
djangorestframework = "3.13.1"
cmake = "~3.21.1"

[tool.poetry.group.dev.dependencies]
autopep8 = ">=1.5.6"

[build-system]
requires = ["poetry>=0.12"]
build-backend = "poetry.masonry.api"
```

to this:
```toml
[build-system]
build-backend = [ "poetry.core.masonry.api", "poetry.masonry.api",]
requires = [ "poetry-core>=1.0.0", "poetry>=0.12",]

[tool.poetry]
authors = [ "Me", "Somebody",]
description = "Some words"
name = [ "project 1", "project 2",]
version = "1.6.0"

[tool.poetry.dependencies]
"pdfminer.six" = [ "^20220524", "^2022333333334",]
ansi2html = "^1.7"
beautifulsoup4 = "^4.10.0"
boto3 = "^1.16.56"
chardet = "^4.0.0"
cmake = [ "^3.21.1", "~3.21.1",]
Django = "~3.1"
django-allauth = "^0.51"
django-rosetta = "^0.9.5"
djangorestframework = "3.13.1"
other_package = [ "1", "2",]

[tool.poetry.dependencies.torch]
source = "pytorch"
version = "1.10.1+cu113"

[tool.poetry.dependencies.torchvision]
source = "pytorch"
version = "0.11.2+cu113"

[tool.poetry.group.dev.dependencies]
autopep8 = [ "^1.5", ">=1.5.6",]
black = "~21.8b0"
ipython = "^8.0"
pylint-django = "^2.3.0"
pytest-django = "^4.5.2"
```

As u see, some of packages has confict versions. In this case the report file is created and contains the sources of this conflicts:
```json
"pdfminer.six": {
    "^20220524": [
    "input/file1.toml",
    "input/file3.toml"
    ],
    "^2022333333334": [
    "input/file2.toml"
    ]
},
"cmake": {
    "^3.21.1": [
    "input/file1.toml"
    ],
    "~3.21.1": [
    "input/file3.toml"
    ]
},
"other_package": {
    "1": [
    "input/file1.toml"
    ],
    "2": [
    "input/file2.toml"
    ]
}
```

## Overrides

There is the ability to override some items in target `*.toml` file. Use syntax:

```python
toml_union_process(
    files=Path('input').glob('*.toml'),
    outfile='output.toml',
    report='report.json',

    overrides={
        'tool.poetry.name': 'union',
        'tool.poetry.version': '12'
    }
)
```

In the result u will have:
```toml
[tool.poetry]
name = "union"
version = "12"
```

## CLI

Equivalent CLI command:
```sh
python toml_union.py examples/input/file1.toml examples/input/file2.toml examples/input/file3.toml -o output.toml -r report.json -k tool.poetry.name=union -k tool.poetry.version=12
```

Help message:

```sh
venv/bin/python toml_union.py -h
usage: toml_union.py [-h] [--output OUTFILE] [--unicode-escape] [--report REPORT] [--remove-field [REMOVE_FIELDS [REMOVE_FIELDS ...]]] [--key-value KEY=VALUE] [--ckey-value KEY=VALUE] INPUT [INPUT ...]

Combines several toml files to one with conflicts showing

positional arguments:
  INPUT                 input toml files paths

optional arguments:
  -h, --help            show this help message and exit
  --output OUTFILE, -o OUTFILE
                        output toml file path (default: None)
  --unicode-escape, -u  whether to try to escape unicode sequences in the outfile, useful when outfile has many slashes and codes (default: False)
  --report REPORT, -r REPORT
                        path to report json on failure (default: None)
  --remove-field [REMOVE_FIELDS [REMOVE_FIELDS ...]], -e [REMOVE_FIELDS [REMOVE_FIELDS ...]]
                        Fields to remove. May appear multiple times (default: None)
  --key-value KEY=VALUE, -k KEY=VALUE
                        Add key/value params. May appear multiple times (default: {})
  --ckey-value KEY=VALUE, -c KEY=VALUE
                        Same as --key-value but will be performed only on conflict cases (default: {})

```
