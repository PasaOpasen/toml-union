
from typing import Dict, Any, List, Union, Iterable, Callable, Optional

import sys
import os
from pathlib import Path
import copy
import json
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce

import argparse

import toml


#region TYPES


@dataclass
class TomlValue:
    """
    information about values and their sources
    """

    map: Dict[str, List[int]]
    """
    map: value -> list of its sources
    
    in perfect case it has only one item
    """

    def __len__(self):
        return len(self.map)

    @staticmethod
    def from_value(value: str, index: int):
        """initial constructor"""
        return TomlValue(
            {value: [index]}
        )

    def add(self, value: str, index: int):
        d = self.map
        if value in d:
            d[value].append(index)
        else:
            d[value] = [index]

    def update(self, obj: 'TomlValue'):
        """union current value with new"""
        d = self.map
        for v, indexes in obj.map.items():
            if v in d:
                d[v] += indexes
            else:
                d[v] = indexes

    @staticmethod
    def union_list(items: List['TomlValue']) -> List['TomlValue']:
        """
        unions equal items in list to one and returns list with unique objects

        Args:
            items:

        Returns:

        Notes:
            Inside the pipeline the objects inside lists always have one value
        """

        total_dict: Dict[str, List[int]] = {}

        for it in items:
            for k, v in it.map.items():
                if k in total_dict:
                    total_dict[k] += v
                else:
                    total_dict[k] = v

        return [
            TomlValue(
                {v: indexes}
            )
            for v, indexes in total_dict.items()
        ]

    def to_json(self) -> Union[str, Dict[str, List[int]]]:
        d = self.map
        if len(d) == 1:
            return list(d.keys())[0]
        return d

    def to_toml(self) -> Union[str, List[str]]:
        keys = list(self.map.keys())
        if len(keys) == 1:
            return keys[0]
        return keys


TOML_DICT = Union[Dict[str, Any], Dict[str, 'TOML_DICT']]
"""toml dict type"""


DATA_DICT = Union[
    Dict[str, Union[TomlValue, List[TomlValue]]],
    Dict[str, 'DATA_DICT']
]
"""recursive type for toml file with sources info for values"""


#endregion


#region UTILS

SEP = '___'
"""list to dicts separator"""


def mkdir_of_file(file_name: Union[str, os.PathLike]):
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)


def sort_dict(dct: TOML_DICT) -> TOML_DICT:
    res = {}
    for k in sorted(
        dct.keys(),
        key=lambda s: ('-' if '.' in s else '') + s.lower()
    ):
        v = dct[k]
        res[k] = sort_dict(v) if isinstance(v, dict) else v
    return res


def disable_lists_dict(dct: TOML_DICT) -> TOML_DICT:
    """
    replace constructions like

        [[tool.poetry.source]]
        name = "pytorch"
        priority = "explicit"

        [[tool.poetry.source]]
        name = "PyPI"
        priority = "primary"

    to something like this:
        [tool.poetry.source___pytorch]
        priority = "explicit"

        [tool.poetry.source___PyPI]
        priority = "primary"
    """

    def process(data: TOML_DICT) -> TOML_DICT:
        d = copy.deepcopy(data)

        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):  # it is the list of dicts
                new_dicts = {
                    f"{k}{SEP}{item['name']}": process({_k: _v for _k, _v in item.items() if _k != 'name'})
                    for item in v
                }
                """new dict with processed dicts of list items with updated names"""
                d.pop(k)
                d.update(new_dicts)
            elif isinstance(v, dict):  # go deeper
                d[k] = process(v)

        return d

    return process(dct)


def enable_lists_dicts(dct: TOML_DICT) -> TOML_DICT:
    """reverses disable_lists_dict effect"""

    def process(data: TOML_DICT) -> TOML_DICT:
        d = copy.deepcopy(data)

        list_dicts: Dict[str, List[TOML_DICT]] = defaultdict(list)
        """recovered dictionaries which contain lists of dicts"""

        for k, v in data.items():

            if isinstance(v, dict):
                v = process(v)  # go deeper
                if SEP in k:  # move to storage
                    parent, name = k.split(SEP, 1)
                    v['name'] = name
                    list_dicts[parent].append(v)
                    d.pop(k)  # remove this version from result
                else:  # just keep in result
                    d[k] = v

        d.update(dict(list_dicts))

        return d

    return process(dct)


def read_toml(file_name: Union[str, os.PathLike]) -> TOML_DICT:
    with open(file_name, 'r', encoding='utf-8') as f:
        content = toml.load(f)

    content = disable_lists_dict(content)

    return content


def write_toml(file_name: Union[str, os.PathLike], data: TOML_DICT):
    mkdir_of_file(file_name)
    data = enable_lists_dicts(data)
    data = sort_dict(data)
    with open(file_name, 'w', encoding='utf-8') as f:
        toml.dump(data, f)


def write_json(file_name: Union[str, os.PathLike], data: TOML_DICT):
    mkdir_of_file(file_name)
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def to_data_dict(dct: TOML_DICT, index: int = 0) -> DATA_DICT:
    """
    converts dict to data dict

    Args:
        dct:
        index: label of this dict to keep in data

    Returns:

    """

    result: TOML_DICT = {}

    for key, value in dct.items():
        if isinstance(value, dict):  # go deeper
            result[key] = to_data_dict(value, index)
        else:
            assert isinstance(value, (list, str, int)), f"unexpected value {value} type: {type(value)}"

            if isinstance(value, list):
                result[key] = [
                    TomlValue.from_value(v, index) for v in value
                ]
            else:
                result[key] = TomlValue.from_value(value, index)

    return result


def to_dict(dct: DATA_DICT, converter: Callable[[TomlValue], Any] = TomlValue.to_toml) -> TOML_DICT:
    """converts data dict to simple toml dict"""
    res = {}

    for k, v in dct.items():
        if isinstance(v, dict):
            res[k] = to_dict(v, converter=converter)
        elif isinstance(v, list):
            res[k] = [converter(obj) for obj in v]
        else:
            res[k] = converter(v)

    return res


def union_2_data_dicts(d1: DATA_DICT, d2: DATA_DICT) -> DATA_DICT:

    d1: DATA_DICT = copy.deepcopy(d1)

    for key, v2 in d2.items():
        if key in d1:
            v1 = d1[key]
            assert type(v1) == type(v2), f"incompatible types {v1} and {v2}"

            if isinstance(v1, list):
                d1[key] = TomlValue.union_list(v1 + v2)
            elif isinstance(v1, dict):
                d1[key] = union_2_data_dicts(v1, v2)
            else:
                assert isinstance(v1, TomlValue)
                d1[key].update(v2)

        else:
            d1[key] = v2

    return d1


def union_dicts(dicts: Iterable[TOML_DICT]) -> DATA_DICT:

    dicts = [
        to_data_dict(dct, i) for i, dct in enumerate(dicts)
    ]
    """input data as ready data dicts"""

    if len(dicts) == 1:
        return dicts[0]

    dct = reduce(
        union_2_data_dicts, dicts
    )

    return dct


def override_param(
    dct: DATA_DICT,
    route: str,
    value: Union[str, List[str]],
    only_on_conflict: bool = False
):
    """
    performs override operation
    Args:
        dct: target dict
        route: path to value like dct1.dct2.dct3.key
        value: value to put
        only_on_conflict: perform operation only on conflict in the param

    """

    if '.' not in route:  # no steps inside, perform main action
        if (
            only_on_conflict and
            (
                route not in dct or
                len(dct[route]) < 2
            )
        ):  # do not override if no conflicts there
            return
        dct[route] = TomlValue.from_value(value, -1)
        return

    key, rt = route.split('.', maxsplit=1)
    if key not in dct:
        if only_on_conflict:  # break the operation
            return
        dct[key] = {}
    override_param(dct[key], rt, value, only_on_conflict=only_on_conflict)


def remove_field(dct: Dict, route: str):
    """removes the field on this route from the dict"""

    if '.' not in route:  # no steps inside, perform main action
        dct.pop(route, None)  # remove this key from dict
        return

    key, rt = route.split('.', maxsplit=1)
    if key in dct:  # go deeper and remove tail in subdictionary
        remove_field(dct[key], rt)


#endregion


#region MAIN

def toml_union_process(
    files: Iterable[Union[str, os.PathLike]],
    outfile: Union[str, os.PathLike],
    report: Optional[Union[str, os.PathLike]] = None,
    remove_fields: Optional[Iterable[str]] = None,
    overrides: Dict[str, Any] = None,
    overrides_on_conflicts: Dict[str, Any] = None,
) -> None:
    """
    Union several toml files to one

    Args:
        files: input files or folders with them
        outfile: result file
        report: file to report in case of conflicts, None means disable
        remove_fields: some fields like d1.d2.d3, toml.build and so on -- to remove from target file,
            works before overrides
        overrides: kwargs to override something in result file in form
            "dct1.dct2.key": "value"
        overrides_on_conflicts: same as overrides but will be performed only on conflict fields

    """

    assert files
    if isinstance(files, str):
        files = [files]

    toml_files = []
    for f in files:
        p = Path(f)
        if p.is_file():
            toml_files.append(p)
        else:
            toml_files.extend(
                p.rglob('*.toml')
            )
    
    assert toml_files, f"no such *.toml files in {files}"

    datas: DATA_DICT = union_dicts(
        read_toml(file) for file in toml_files
    )
    """result wide data dict"""

    remove_fields = remove_fields or []
    if remove_fields:
        for r in remove_fields:
            remove_field(datas, r)

    if overrides:
        # override result params
        for k, v in overrides.items():
            override_param(datas, k, v)

    if overrides_on_conflicts:
        for k, v in overrides_on_conflicts.items():
            override_param(datas, k, v, only_on_conflict=True)

    outdict = to_dict(datas)
    """result shortened dict"""
    write_toml(outfile, outdict)

    if report:
        index_file_map: List[str] = [
            str(f) for i, f in enumerate(toml_files)
        ]

        conflict: bool = False
        """flag about some conflicts existence"""

        def serializer(obj: TomlValue):
            """wrapper under class json serializer"""
            nonlocal conflict
            res = obj.to_json()
            if isinstance(res, dict):
                res = {
                    _k: [index_file_map[vv] for vv in _v]
                    for _k, _v in res.items()
                }
                conflict = True  # set flag about conflict
            return res

        outdict = to_dict(datas, converter=serializer)
        if conflict:
            write_json(report, outdict)


#endregion


#region CLI

class kvdictAppendAction(argparse.Action):
    """
    argparse action to split an argument into KEY=VALUE form
    on the first = and append to a dictionary.
    """
    def __call__(self, parser, args, values, option_string=None):
        assert(len(values) == 1)
        try:
            (k, v) = values[0].split("=", 2)
        except ValueError as ex:
            raise argparse.ArgumentError(
                self, f"could not parse argument \"{values[0]}\" as k=v format"
            )
        d = getattr(args, self.dest) or {}
        d[k] = v
        setattr(args, self.dest, d)


parser = argparse.ArgumentParser(
    prog=f"{os.path.basename(__file__)}",
    description='Combines several toml files to one with conflicts showing',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)


parser.add_argument(
    'INPUT', action='store', type=str, nargs='+',
    help='input toml files paths',
)
parser.add_argument(
    '--output', '-o', action='store', type=str,
    help='output toml file path',
    dest='outfile'
)
parser.add_argument(
    '--report', '-r', action='store', type=str, default=None,
    help='path to report json on failure'
)

parser.add_argument(
    "--remove-field", "-e",
    nargs='*',
    action='extend',
    type=str,
    help="Fields to remove. May appear multiple times",
    dest='remove_fields'
)

parser.add_argument(
    "--key-value", "-k",
    nargs=1,
    action=kvdictAppendAction,
    metavar="KEY=VALUE",
    default={},
    type=str,
    help="Add key/value params. May appear multiple times",
    dest='overrides_kwargs'
)

parser.add_argument(
    "--ckey-value", "-c",
    nargs=1,
    action=kvdictAppendAction,
    metavar="KEY=VALUE",
    default={},
    type=str,
    help="Same as --key-value but will be performed only on conflict cases",
    dest='overrides_kwargs_conflict'
)


def main():

    sys.path.append(
        os.path.dirname(os.getcwd())
    )

    args = sys.argv[1:]

    parsed = parser.parse_args(args)

    toml_union_process(
        parsed.INPUT,
        outfile=parsed.outfile,
        report=parsed.report,
        remove_fields=parsed.remove_fields,
        overrides=parsed.overrides_kwargs,
        overrides_on_conflicts=parsed.overrides_kwargs_conflict
    )

    print()


#endregion


if __name__ == '__main__':
    main()








