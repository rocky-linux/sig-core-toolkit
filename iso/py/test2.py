#!/usr/bin/env python3

import desert
from attrs import define, field
import typing as t

CONFIG = {
    "8": {
        "allowed_arches": ["x86_64", "aarch64"],
        "repo_url_list": ["some", "shit", "here"]
    },
    "9": {
        "allowed_arches": ["x86_64", "aarch64", "ppc64le", "s390x"],
        "repo_url_list": ["some", "other", "shit", "here"]
    }
}

@define
class VersionConfig:
    allowed_arches: t.List[str] = field()
    repo_url_list: t.List[str] = field()

    @allowed_arches.validator
    def check(self, attribute, value):
        if not all(v in ["x86_64", "aarch64", "ppc64le", "s390x"] for v in value):
            raise ValueError("Architecture list does not match")

def new(version):
    schema = desert.schema(VersionConfig)
    config = CONFIG[str(version)]
    return schema.load(config)

eight = new(8)
nine  = new(9)

print(eight)
print(eight.allowed_arches)
print(nine)
