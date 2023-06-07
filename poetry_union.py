
from typing import Dict, Any, List, Union, Iterable, Callable, Optional

import os
from pathlib import Path
import copy
import json
from dataclasses import dataclass
from functools import reduce

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

def mkdir_of_file(file_name: Union[str, os.PathLike]):
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)


def read_toml(file_name: Union[str, os.PathLike]) -> TOML_DICT:
    with open(file_name, 'r', encoding='utf-8') as f:
        content = toml.load(f)
        return content


def write_toml(file_name: Union[str, os.PathLike], data: TOML_DICT):
    mkdir_of_file(file_name)
    with open(file_name, 'w', encoding='utf-8') as f:
        toml.dump(data, f)


def write_json(file_name: Union[str, os.PathLike], data: TOML_DICT):
    mkdir_of_file(file_name)
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


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
            assert isinstance(value, (list, str)), f"unexpected value {value} type: {type(value)}"

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


#endregion


#region MAIN

#TODO add overrides     -1 file, no conflict
def poetry_union_process(
    files: Iterable[Union[str, os.PathLike]],
    outfile: Union[str, os.PathLike],
    report: Optional[Union[str, os.PathLike]] = None
) -> None:
    """
    Union several toml files to one

    Args:
        files: input files
        outfile: result file
        report: file to report in case of conflicts, None means disable

    """


    files = list(files)

    datas: DATA_DICT = union_dicts(
        read_toml(file) for file in files
    )
    """result wide data dict"""

    outdict = to_dict(datas)
    """result shortened dict"""
    write_toml(outfile, outdict)

    if report:
        index_file_map: List[str] = [
            str(f) for i, f in enumerate(files)
        ]

        conflict: bool = False
        """flag about some conflicts existence"""

        def serializer(obj: TomlValue):
            """wrapper under class json serializer"""
            nonlocal conflict
            res = obj.to_json()
            if isinstance(res, dict):
                res = {
                    k: [index_file_map[vv] for vv in v]
                    for k, v in res.items()
                }
                conflict = True  # set flag about conflict
            return res

        outdict = to_dict(datas, converter=serializer)
        if conflict:
            write_json(report, outdict)


#endregion


#region CLI


#endregion











