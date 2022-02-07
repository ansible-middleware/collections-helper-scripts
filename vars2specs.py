# Copyright (C) 2022 Guido Grazioli <guido.grazioli@gmail.com>
# SPDX-License-Identifier: MIT
#
# pylint: disable=invalid-name
"""Generates arguments_spec.yml from variables parsed in role.

Usage:
  vars2specs.py [-c] [-r DIR] [-o DIR]

Options:
  -c                       Parse all roles in a collection [default: no]
  -r DIR --role_dir=DIR    Input role directory [default: ./roles/].
  -o DIR --output_dir=DIR  Output directory for argument specs [default: ./meta/].
"""
import typing
import yaml
import docopt
import glob
import sys
import re

from ruamel.yaml import YAML

from yaml.composer import Composer
from yaml.constructor import Constructor
from yaml.nodes import ScalarNode
from yaml.resolver import BaseResolver
from yaml.loader import SafeLoader

from pathlib import Path

LINE_NUMBER_KEY: str = "__line__"


class LineLoader(SafeLoader):
    """
    Custom LineLoader which return line number for all variables (not just parsed nodes).
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


class Vars2Specs:
    """
    class to generate arguments_spec.yml from parsed variables
    """
    role_dir: Path
    output: Path
    collection: bool


    def __init__(self, role: str, output: str, collection: bool):
        self.role_dir: Path = Path(role)
        self.output: Path = Path(output + '/arguments_spec.yml')
        self.collection = collection


    def lookup_var_files(self):
        """ find var files """
        if self.collection:
            return glob.glob(str(self.role_dir)+'/**/defaults/*.yml') + glob.glob(str(self.role_dir)+'/**/vars/*.yml')
        return glob.glob(str(self.role_dir)+'/defaults/*.yml') + glob.glob(str(self.role_dir)+'/vars/*.yml')


    def generate_spec(self, path: Path):
        """ parse variables """
        results = []
        variables = yaml.load(path, Loader=LineLoader)
        rel_path = Path(path.name).relative_to(self.role_dir)
        for var_name in filter(lambda k: not k.startswith(LINE_NUMBER_KEY) and not isinstance(variables[k],dict), variables.keys()):
            default = 'default: "'+re.sub('\\\\',"\\\\\\\\",str(variables[var_name]))+'"' if variables[var_name] else 'required: true'
            linenumber = variables[LINE_NUMBER_KEY+var_name]
            results.append("""\
            %s:
                # line %s of %s
                %s
                description: ''
                type: "str"
            """ % (var_name, linenumber, str(rel_path), default))

        return results


    def generate(self):
        """ write argument specs """
        variable_specs = []
        for var_file in self.lookup_var_files():
            print("Parsing %s" % var_file)
            with open(var_file, 'r') as f:
                variable_specs += self.generate_spec(f)
                #print(variable_specs)
              
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=4)
        yaml.width = 800
        with open('arguments_spec.yml', 'w') as f:
            root = """\
            argument_specs: 
                main: 
                    options: 
            """
            root_yml = yaml.load(root)
            code_yml = yaml.load('\n'.join(variable_specs))
            root_yml['argument_specs']['main']['options'] = code_yml
            yaml.dump(root_yml, f)

        return


def main():
    args = docopt.docopt(__doc__)
    role_dir = args['--role_dir'] or 'roles/'
    output_dir = args['--output_dir'] or 'meta/'
    collection = args['-c'] or False
    v2s = Vars2Specs(role_dir, output_dir, collection)
    v2s.generate()


if __name__ == '__main__':
    main()

