# Copyright (C) 2022 Guido Grazioli <guido.grazioli@gmail.com>
# SPDX-License-Identifier: MIT
#
# pylint: disable=invalid-name
"""Generates argument_specs.yml from variables parsed in role.

Usage:
  vars2specs.py [-c] [-r DIR]

Options:
  -c                       Parse all roles in a collection [default: no]
  -r DIR --role_dir=DIR    Input role directory [default: ./].
"""
import typing
import yaml
import docopt
import glob
import re
import collections

from ruamel.yaml import YAML

from yaml.composer import Composer
from yaml.constructor import Constructor
from yaml.nodes import ScalarNode
from yaml.resolver import BaseResolver
from yaml.loader import SafeLoader

from pathlib import Path

LINE_NUMBER_KEY: str = "__line__"
ARGUMENTS_SPEC_FILE: str = "argument_specs.yml"
ARGUMENTS_SPEC_PATH: str = "/meta/" + ARGUMENTS_SPEC_FILE
ARGUMENTS_SPEC_DICT: str = """\
argument_specs:
    main:
        options:
"""

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


    def lookup_var_files(self, role):
        """ find var files """
        if self.collection:
            return glob.glob(str(self.role_dir)+'/'+role+'/defaults/*.yml') + glob.glob(str(self.role_dir)+'/'+role+'/vars/*.yml')
        return glob.glob(str(self.role_dir)+'/defaults/*.yml') + glob.glob(str(self.role_dir)+'/vars/*.yml')


    def quote_default(self, value, vartype):
        escaped = re.sub('\\\\', "\\\\\\\\", str(value))
        return '"' + escaped + '"' if vartype not in [ "bool", "int" ] else value


    def generate_spec(self, path: Path, defined_vars):
        """ parse variables """
        results = []
        variables = yaml.load(path, Loader=LineLoader)
        rel_path = Path(path.name).relative_to(self.role_dir)
        for var_name in filter(lambda k: not k.startswith(LINE_NUMBER_KEY) and not isinstance(variables[k],dict), variables.keys()):
            linenumber = variables[LINE_NUMBER_KEY + var_name]
            try:
                description = defined_vars[var_name]['description']
            except KeyError:
                description = "TODO document argument"
            try:
                vartype = defined_vars[var_name]['type']
            except KeyError:
                vartype = type(variables[var_name]).__name__ if variables[var_name] is not None else "str"
            default = "default: %s" % self.quote_default(variables[var_name], vartype) if variables[var_name] is not None else 'required: true'
            results.append("""\
            %s:
                # line %s of %s
                %s
                description: "%s"
                type: "%s"
            """ % (var_name, linenumber, str(rel_path), default, description, vartype))
        return results


    def load_existing_specs(self, role):
        print("Parsing argument_specs for role %s" % role)
        try:
            with open(str(self.role_dir) + '/' + role + ARGUMENTS_SPEC_PATH, 'r') as specs:
                specs = yaml.load(specs, Loader=LineLoader)
                return specs['argument_specs']['main']['options']
        except:
            return {}


    def generate(self):
        """ write argument specs """
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=4)
        yaml.width = 800

        variable_specs = collections.defaultdict(list)
        roles = self.lookup_roles()
        for role in roles:
            defined_vars = self.load_existing_specs(role)
            for var_file in self.lookup_var_files(role):
                print("Parsing %s for role %s" % (var_file, role))
                with open(var_file, 'r') as f:
                    variable_specs[role] += self.generate_spec(f, defined_vars)

        root_yml = yaml.load(ARGUMENTS_SPEC_DICT)
        for role in roles:
            specfile = str(self.role_dir)  + ARGUMENTS_SPEC_PATH
            if self.collection:
                specfile = str(self.role_dir) + '/' + role + ARGUMENTS_SPEC_PATH
            if len(variable_specs[role]) > 0:
                print("Writing argument_specs for role %s: %s" % (role, specfile))
                with open(specfile, 'w') as f:
                    code_yml = yaml.load('\n'.join(variable_specs[role]))
                    root_yml['argument_specs']['main']['options'] = code_yml
                    yaml.dump(root_yml, f)
            else:
                print("No variables found for role directory %s" % self.role_dir)


def main():
    args = docopt.docopt(__doc__)
    role_dir = args['--role_dir'] or './'
    collection = args['-c'] or False
    v2s = Vars2Specs(role_dir, collection)
    v2s.generate()


if __name__ == '__main__':
    main()
