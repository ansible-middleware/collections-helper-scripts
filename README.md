# ansible collections doc helper scripts

Helper scripts to generate documentation for role arguments.

## Installation

Install dependencies:

    pip install -r requirements.txt

Then:

    python <script.py> [-c] [--role_dir=<role_dir>]

The scripts will generate `meta/argument_specs.yml` for each new parsed variable; and using argument_specs.yml, can generate README.md tabular documentation.

Scripts were tested with python 3.9+

If you are looking for ansible-lint rules to check argument_specs.yml against var-files, see [our custom rules](https://github.com/ansible-middleware/ansible-lint-custom-rules).


## Usage


### vars2specs.py


Parses role default/main.yml and varrs/main.yml and for each unspecified arguments creates elements in `argument_specs.yml`

```
Generates argument_specs.yml from variables parsed in role.

Usage:
  vars2specs.py [-c] [-r DIR]

Options:
  -c                       Parse all roles in a collection [default: no]
  -r DIR --role_dir=DIR    Input role directory [default: ./].
```


### specs2readme.py

The script will look for the following placeholder in README.md:
```
<!--start argument_specs-->
[...]
<!--end argument_specs-->
```

and add any undefined variable or default reading the specification in `meta/argument_specs.yml` under the following headings:

```
Role Variables
--------------

| Variable | Description | Required |
|:---------|:------------|:---------|
>> required variables will be added here
|`i_am_required`| give value to me | `yes` |
** other already listed variables will be left untouched


Role Defaults
-------------

| Variable | Description | Default |
|:---------|:------------|:--------|
>> defaults with be added here
|`know_what_you_doing`| override if needed | `false` |
** other already listed default will be left untouched
```


Usage:

```
Generates README.md docs from argument_specs.yml.

Usage:
  specs2readme.py [-c] [-r DIR] [-d] [-2] [-n]

Options:
  -c --collection          Parse all roles in a collection [default: no]
  -r DIR --role_dir=DIR    Input role directory [default: ./].
  -d --dry-run             Dry-run, write to standard output [default: no]
  -2 --two-columns         Use two columns table format instead of three columns [default: no]
  -n --no-diff             Emit all variables, not only the specs not already in README.md [default: no]
```


## License

Apache License v2.0 or later

See [LICENSE](LICENSE) to view the full text.
