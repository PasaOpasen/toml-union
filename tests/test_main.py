
import os

from toml_union import toml_union_process, read_toml, to_dict

CUR_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.dirname(CUR_DIR)


def test_1():

    result = os.path.join(PROJECT_DIR, 'tmp', 'test1.toml')

    toml_union_process(
        files=os.path.join(CUR_DIR, 'input', 'test_1'),
        outfile=result,
        remove_fields=[
            'build-system',
            'tool.poetry.version'
        ],
        overrides={
            'tool.poetry.description': 'overridden'
        },
        overrides_on_conflicts={
            'tool.poetry.authors': 'conflict author',
            'tool.poetry.dependencies.torch.source': 'no conflict, will not be overriden'
        }
    )

    d1 = read_toml(result)
    d2 = read_toml(os.path.join(CUR_DIR, 'output', 'test_1', 'test1.toml'))

    assert d1 == d2




