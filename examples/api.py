
from pathlib import Path

from poetry_union import poetry_union_process


if __name__ == '__main__':

    poetry_union_process(
        files=Path('input').glob('*.toml'),
        outfile='output.toml',
        report='report.json',

        **{
            'tool.poetry.version': "12"
        }
    )
