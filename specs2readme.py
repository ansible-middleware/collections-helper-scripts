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


ARGUMENTS_SPEC_FILE: str = "argument_specs.yml"
ARGUMENTS_SPEC_PATH: str = "/meta/" + ARGUMENTS_SPEC_FILE


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


    def lookup_roles(self):
        """ find roles """
        if self.collection:
            return [
                Path(role).name
                for role in glob.glob(str(self.role_dir)+'/**/')
            ]
        return [self.role_dir.name]


    def find_arguments_marker(self):
        return


    def generate(self):
        roles = self.lookup_roles()
        for role in roles:
            specs_path: Path = self.role_dir / "meta" / "argument_specs.yml"
            if not specs_path.exists():
                print("error: argument_specs not found for role %s", role)
                exit(1)
            with open(specs_path, 'r') as f:
                argument_specs = yaml.load(f, Loader=LineLoader)


def main():
    args = docopt.docopt(__doc__)
    role_dir = args['--role_dir'] or './'
    collection = args['-c'] or False
    s2rm = Specs2Readme(role_dir, collection)
    s2rm.generate()


if __name__ == '__main__':
    main()
