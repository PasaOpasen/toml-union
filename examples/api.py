
from pathlib import Path

from toml_union import toml_union_process


if __name__ == '__main__':

    toml_union_process(
        files=Path('input').glob('*.toml'),
        outfile='output.toml',
        report='report.json',

        overrides={
            'tool.poetry.name': 'union',
            'tool.poetry.version': '12'
        }
    )
