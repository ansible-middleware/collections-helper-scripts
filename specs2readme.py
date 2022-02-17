# Copyright (C) 2022 Guido Grazioli <guido.grazioli@gmail.com>
# SPDX-License-Identifier: MIT
#
# pylint: disable=invalid-name
"""Generates README.md docs from argument_specs.yml.

Usage:
  specs2readme.py [-c] [-r DIR]

Options:
  -c                       Parse all roles in a collection [default: no]
  -r DIR --role_dir=DIR    Input role directory [default: ./].
"""
import typing
import yaml
import docopt
import glob
import re

from yaml.composer import Composer
from yaml.constructor import Constructor
from yaml.nodes import ScalarNode
from yaml.resolver import BaseResolver
from yaml.loader import SafeLoader

from pathlib import Path


LINE_NUMBER_KEY: str = "__line__"
ARGUMENTS_SPEC_FILE: str = "argument_specs.yml"
ARGUMENTS_SPEC_PATH: str = "/meta/" + ARGUMENTS_SPEC_FILE
MD_MARKER_START: str = "<!--start argument_specs-->"
MD_MARKER_END: str = "<!--end argument_specs-->"

VARS_REGEX       = r"^[|]\s*[`](.*?)[`]\s*[|].*[|]$"
VARS_TITLE:  str = """\
Role Variables
--------------
"""
VARS_HEADER: str = """\
| Variable | Description |
|:---------|:------------|
"""

DEFAULTS_REGEX = r"^[|]\s*[`](.*?)[`]\s*[|][^|]*[|].*[|]$"
DEFAULTS_TITLE: str  = """\
Role Defaults
-------------
"""
DEFAULTS_HEADER: str = """\
| Variable | Description | Default |
|:---------|:------------|:--------|
"""


class LineLoader(SafeLoader):
    """
    Custom LineLoader which return line number for all variables
    (not just parsed nodes).
    """
    def __init__(self, stream):
        super(LineLoader, self).__init__(stream)

    def compose_node(self, parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = self.line
        node = Composer.compose_node(self, parent, index)
        node.__line__ = line + 1
        return node

    def construct_mapping(self, node, deep=False):
        node_pair_lst = node.value
        node_pair_lst_for_appending = []

        for key_node, value_node in node_pair_lst:
            shadow_key_node = ScalarNode(tag=BaseResolver.DEFAULT_SCALAR_TAG, value=LINE_NUMBER_KEY + key_node.value)
            shadow_value_node = ScalarNode(tag=BaseResolver.DEFAULT_SCALAR_TAG, value=key_node.__line__)
            node_pair_lst_for_appending.append((shadow_key_node, shadow_value_node))

        node.value = node_pair_lst + node_pair_lst_for_appending
        mapping = Constructor.construct_mapping(self, node, deep=deep)
        return mapping


class Specs2Readme:
    """
    class to generate README.md doc snippets from ansible argument_specs.yml
    """
    role_dir: Path
    collection: bool


    def __init__(self, role: str, collection: bool):
        self.collection = collection
        self.role_dir: Path = Path(role)
        if collection:
            self.role_dir = self.role_dir / "roles"
        print("Work directory: %s" % self.role_dir)


    def lookup_roles(self) -> list:
        """ find roles """
        if self.collection:
            return [
                Path(role).name
                for role in glob.glob(str(self.role_dir)+'/**/')
            ]
        return [self.role_dir.name]


    def get_readme_arguments_marker(self, role: str):
        readme_path: Path = self.role_dir / role / "README.md"
        if not readme_path.exists():
            print("error: README.md not found for role %s", role)
            exit(2)
        with open(str(readme_path), 'r') as f:
            contents = f.read()
            return contents[contents.find(MD_MARKER_START)+len(MD_MARKER_START):contents.find(MD_MARKER_END)]
        return None


    def load_documented_specs(self, readme: str) -> dict:
        return { "defaults": re.findall(DEFAULTS_REGEX, readme, re.M), "vars": re.findall(VARS_REGEX, readme, re.M) }


    def append_to_readme(self, role: str, newdefs: list, newvars: list):
        readme_path: Path = self.role_dir / role / "README.md"
        with open(str(readme_path), 'r+') as fd:
            contents = fd.readlines()
            if len(newdefs) > 0:
                for index, line in enumerate(contents):
                    if DEFAULTS_TITLE in (contents[index - 1] + line):
                        contents.insert(index + 2, DEFAULTS_HEADER+'\n'.join(newdefs)+'\n\n\n')
                        break
            if len(newvars) > 0:
                for index, line in enumerate(contents):
                    if VARS_TITLE in (contents[index - 1] + line):
                        contents.insert(index + 2, VARS_HEADER+'\n'.join(newvars)+'\n\n\n')
                        break
            if len(newdefs) + len(newvars) > 0:
                fd.seek(0)
                print("writing updated README.md for role %s" % role)
                fd.writelines(contents)


    def generate(self):
        roles = self.lookup_roles()
        for role in roles:
            print("Parsing role %s" % role)
            readme_section = self.get_readme_arguments_marker(role)
            if (readme_section is None):
                print("error: no argument_specs markers found in README.md for role %s", role)
                exit(3)
            documented_vars = self.load_documented_specs(readme_section)
            specs_path: Path = self.role_dir / role / "meta" / "argument_specs.yml"
            if not specs_path.exists():
                print("error: argument_specs not found for role %s" % role)
                exit(1)
            new_vars = { 'vars': [], 'defaults': []}
            with open(specs_path, 'r') as f:
                argument_specs = yaml.load(f, Loader=LineLoader)['argument_specs']['main']['options']
                for var in filter(lambda k: not k.startswith(LINE_NUMBER_KEY), argument_specs.keys() if argument_specs is not None else []):
                    if 'default' in argument_specs[var] and not var in documented_vars['defaults']:
                        print("found missing argument_specs DEFAULT %s to README.md" % var)
                        new_vars["defaults"].append(f"|`{var}`| {argument_specs[var]['description'] } | `{argument_specs[var]['default'] }` |")
                    if 'default' not in argument_specs[var] and not var in documented_vars['vars']:
                        print("found missing argument_specs REQUIRED VAR %s to README.md" % var)
                        new_vars["vars"].append(f"|`{var}`| {argument_specs[var]['description'] } |")

            self.append_to_readme(role, new_vars['defaults'], new_vars['vars'])


def main():
    args = docopt.docopt(__doc__)
    role_dir = args['--role_dir'] or './'
    collection = args['-c'] or False
    s2rm = Specs2Readme(role_dir, collection)
    s2rm.generate()


if __name__ == '__main__':
    main()
