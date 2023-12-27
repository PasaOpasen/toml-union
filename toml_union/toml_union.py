
"""
python toml_union.py -h
"""

from typing import Dict, Any, List, Union, Iterable, Callable, Optional

import sys
import os
from pathlib import Path
import copy
import json
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
import tempfile

import argparse

import toml


#region TYPES

def _add_sources_to_dict(dct: Dict[str, List[int]], key: str, value: Union[int, List[int]]):
    """
    adds new value-source pair to { value -> sources dict }
    Args:
        dct:
        key:
        value:

    Returns:

    >>> _ = _add_sources_to_dict
    >>> d = {}
    >>> _(d, '1', 1); _(d, '1', 2); _(d, '2', [21, 22]); _(d, '2', 23); _(d, '1', [3]); d
    {'1': [1, 2, 3], '2': [21, 22, 23]}
    """
    if key in dct:
        if isinstance(value, int):
            dct[key].append(value)
        else:
            dct[key].extend(value)
    else:
        if isinstance(value, int):
            dct[key] = [value]
        else:
            dct[key] = value.copy()



@dataclass
class TomlValue:
    """
    information about values and their sources

    values creation:
    >>> t = TomlValue.from_value('a', 0)
    >>> t.add('a', 1); t.add('b', [1, 2])
    >>> t
    TomlValue(map={'a': [0, 1], 'b': [1, 2]})
    >>> t2 = TomlValue.from_value('b', 4); t2.add('c', 7); t2
    TomlValue(map={'b': [4], 'c': [7]})
    >>> t3 = TomlValue.from_value('c', 5); t3.add('d', [4, 5, 6])

    union values with split by unique:
    >>> TomlValue.union_list([t, t2, t3])
    [TomlValue(map={'a': [0, 1]}), TomlValue(map={'b': [1, 2, 4]}), TomlValue(map={'c': [7, 5]}), TomlValue(map={'d': [4, 5, 6]})]

    update existing value:
    >>> t.update(t2); t
    TomlValue(map={'a': [0, 1], 'b': [1, 2, 4], 'c': [7]})

    """

    map: Dict[str, List[int]]
    """
    map: value -> list of its sources
    
    in perfect case it has only one item what means that all sources have same value in that field;
        otherwise there will be conflict and the map will contain information about them
    """

    def __len__(self):
        return len(self.map)

    def __str__(self):
        return 'TomlValue  ' + ' ; '.join(f"{k} -> {tuple(v)}" for k, v in self.map.items())

    @staticmethod
    def from_value(value: str, index: int):
        """initial constructor"""
        return TomlValue(
            {value: [index]}
        )

    def add(self, value: str, index: Union[int, List[int]]):
        _add_sources_to_dict(self.map, value, index)

    def update(self, obj: 'TomlValue'):
        """union current value with new"""
        d = self.map
        for v, indexes in obj.map.items():
            _add_sources_to_dict(d, v, indexes)

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
                _add_sources_to_dict(total_dict, k, v)

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


def _sorter_key(s: str) -> str:
    """key function for dict keys sort"""
    return ('-' if '.' in s else '') + s.lower()


def sort_dict(dct: TOML_DICT) -> TOML_DICT:
    """
    performs dictionary deep sort
    Args:
        dct:

    Returns:
        sorted dictionary

    >>> sort_dict({'1': 2, 'a': [3, 4], 'a.b': {'2': [3, 5], '1': 3}, 'c': ['a', 'b']})
    {'a.b': {'1': 3, '2': [3, 5]}, '1': 2, 'a': [3, 4], 'c': ['a', 'b']}
    """
    res = {}
    for k in sorted(dct.keys(), key=_sorter_key):
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

    Notes:
        extracts dict using 'name' field
    """

    def process(data: TOML_DICT) -> TOML_DICT:
        d = copy.deepcopy(data)

        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):  # it is the list of dicts

                assert all('name' in item for item in v), v

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
    """
    reverses disable_lists_dict effect

    >>> t = dict(root=[{'name': 'name1', 'other': '1', 'data': 'data1'}, {'name': 'name2', 'other': '2', 'data': 'data2'}])
    >>> converted = disable_lists_dict(t); converted
    {'root___name1': {'other': '1', 'data': 'data1'}, 'root___name2': {'other': '2', 'data': 'data2'}}
    >>> enable_lists_dicts(converted)
    {'root': [{'other': '1', 'data': 'data1', 'name': 'name1'}, {'other': '2', 'data': 'data2', 'name': 'name2'}]}
    """

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


def read_text(file_name: Union[str, os.PathLike]) -> str:
    return Path(file_name).read_text(encoding='utf-8')


def write_text(file_name: Union[str, os.PathLike], text: str):
    mkdir_of_file(file_name)
    Path(file_name).write_text(text, encoding='utf-8')


def read_toml(file_name: Union[str, os.PathLike]) -> TOML_DICT:
    """reads dict from toml with some preprocessing"""
    with open(file_name, 'r', encoding='utf-8') as f:
        content = toml.load(f)

    content = disable_lists_dict(content)

    return content


def write_toml(file_name: Union[str, os.PathLike], data: TOML_DICT, unicode_escape: bool = False):
    """writes dict to toml with some postprocessing"""
    mkdir_of_file(file_name)
    data = enable_lists_dicts(data)
    data = sort_dict(data)
    with open(file_name, 'w', encoding='utf-8') as f:
        toml.dump(data, f)

    if unicode_escape:
        write_text(
            file_name,
            read_text(file_name).encode().decode('unicode_escape').replace('"', "'")
        )


def write_json(file_name: Union[str, os.PathLike], data: TOML_DICT):
    """writes dict to json without special postprocessing"""
    mkdir_of_file(file_name)
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def to_data_dict(dct: TOML_DICT, index: int = 0) -> DATA_DICT:
    """
    converts usual dict to data dict

    Args:
        dct:
        index: label of this dict to keep in data

    Returns:

    >>> to_data_dict(dict(a=1, b = [1, 2], c={'d': 3, 'e': [4, 5], 'f': {'g': '6'}}), index = 9)
    {'a': TomlValue(map={1: [9]}), 'b': [TomlValue(map={1: [9]}), TomlValue(map={2: [9]})], 'c': {'d': TomlValue(map={3: [9]}), 'e': [TomlValue(map={4: [9]}), TomlValue(map={5: [9]})], 'f': {'g': TomlValue(map={'6': [9]})}}}
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
    """
    converts data dict to usual toml dict

    >>> d = dict(a=1, b = [1, 2], c={'d': 3, 'e': [4, 5], 'f': {'g': '6'}})
    >>> assert to_dict(to_data_dict(d)) == d
    """
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
    """
    performs data dicts deep union

    >>> t1 = dict(a=1, b=[2], c={'d': [3, 4]})
    >>> t2 = dict(b=[3], c={'d': [6, 4], 'e': 8})
    >>> union_2_data_dicts(to_data_dict(t1, index=-1), to_data_dict(t2, index=-2))
    {'a': TomlValue(map={1: [-1]}), 'b': [TomlValue(map={2: [-1]}), TomlValue(map={3: [-2]})], 'c': {'d': [TomlValue(map={3: [-1]}), TomlValue(map={4: [-1, -2]}), TomlValue(map={6: [-2]})], 'e': TomlValue(map={8: [-2]})}}
    """

    d1: DATA_DICT = copy.deepcopy(d1)

    for key, v2 in d2.items():
        if key in d1:
            v1 = d1[key]
            assert type(v1) is type(v2), f"incompatible types {v1} and {v2}"

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
    """perform to data dict conversion and data dicts union for all input dicts"""

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

    >>> t1 = dict(main=dict(a=1, b=['2', '3'], c=2))
    >>> t2 = dict(main=dict(a=1, b=['3', '4'], c=3))
    >>> t3 = dict(main=dict(a=1, b=['5'], c=3))
    >>> u = union_dicts([t1, t2, t3]); u
    {'main': {'a': TomlValue(map={1: [0, 1, 2]}), 'b': [TomlValue(map={'2': [0]}), TomlValue(map={'3': [0, 1]}), TomlValue(map={'4': [1]}), TomlValue(map={'5': [2]})], 'c': TomlValue(map={2: [0], 3: [1, 2]})}}
    >>> s=copy.deepcopy(u); override_param(s, route='main.a', value=2); override_param(s, route='main.c', value=4); s
    {'main': {'a': TomlValue(map={2: [-1]}), 'b': [TomlValue(map={'2': [0]}), TomlValue(map={'3': [0, 1]}), TomlValue(map={'4': [1]}), TomlValue(map={'5': [2]})], 'c': TomlValue(map={4: [-1]})}}
    >>> s=copy.deepcopy(u); override_param(s, route='main.a', value=2, only_on_conflict=True); override_param(s, route='main.c', value=4); s
    {'main': {'a': TomlValue(map={1: [0, 1, 2]}), 'b': [TomlValue(map={'2': [0]}), TomlValue(map={'3': [0, 1]}), TomlValue(map={'4': [1]}), TomlValue(map={'5': [2]})], 'c': TomlValue(map={4: [-1]})}}
    """

    if '.' not in route:  # no steps inside, perform main action
        if (
            only_on_conflict and
            (
                route not in dct or
                len(dct[route]) < 2  # only one source -- no conflicts
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
    """
    removes the field on this route from the dict

    >>> d = dict(a=1, b=dict(c=2, d=dict(f=3, e=4)))
    >>> remove_field(d, 'b.d.e'); d
    {'a': 1, 'b': {'c': 2, 'd': {'f': 3}}}
    """

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
    outfile: Optional[Union[str, os.PathLike]] = None,
    report: Optional[Union[str, os.PathLike]] = None,
    remove_fields: Optional[Iterable[str]] = None,
    overrides: Dict[str, Any] = None,
    overrides_on_conflicts: Dict[str, Any] = None,
    unicode_escape: bool = False
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
        unicode_escape: whether to escape unicode sequences

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
    
    if outfile is None:
        _, f = tempfile.mkstemp(prefix='toml-union', text=True)
        write_toml(f, outdict, unicode_escape=unicode_escape)
        print(read_text(f))
        os.unlink(f)
    else: 
        write_toml(outfile, outdict, unicode_escape=unicode_escape)

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
    help='output toml file path, empty value means to print to console',
    dest='outfile'
)

parser.add_argument(
    '--unicode-escape', '-u', action='store_true',
    help='whether to try to escape unicode sequences in the outfile, useful when outfile has many slashes and codes'
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
        overrides_on_conflicts=parsed.overrides_kwargs_conflict,
        unicode_escape=parsed.unicode_escape
    )

    print()


#endregion


if __name__ == '__main__':
    main()








