# From https://gist.github.com/jobevers/49432f6751753cfffea3cd2cddaaa183
# Credit to mitar on stackoverflow: https://stackoverflow.com/a/45390670/2752242

import re
from typing import List, Tuple

import astroid
from pylint import checkers, interfaces
from pylint.checkers import utils

_CONFIG_HEAD_REGEX = re.compile(r',|\.(?={)')


# TODO(cyrille): Add relevant error messages for wrong config.
def _parse_config(config: str) -> List[Tuple[str, str]]:
    if not config:
        return []
    config = re.sub(r'\s+', '', config) + ','
    res = []
    while config:
        module, config = _CONFIG_HEAD_REGEX.split(config, 1)
        if not config.startswith('{'):
            res.append(module.rsplit('.', 1))
            continue
        submodules, config = config[1:].split('},', 1)
        res.extend((module, submodule) for submodule in submodules.split(','))
    return res


class ImportOnlyModulesChecked(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker

    name = 'import_only_modules'
    priority = -1
    msgs = {
        'W5521': (
            'Import "%s" from "%s" is not a module.',
            'import-only-modules',
            'Only modules should be imported.',
        ),
        'W5522': (
            '"%s" from module "%s" should be imported directly.',
            'import-direct-attributes',
            'Specified module members should be imported directly.')
    }

    options = (
        (
            'allowed-direct-imports',
            dict(
                metavar='module1.{import1,import2},module2.import3',
                default='',
                help='A comma-separated list of exceptions. '
                'Imports from the same module can be factorized in curly braces',
            )
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._imports_to_check = {}
        self._exceptions = None

    @property
    def exceptions(self):
        if self._exceptions is None:
            self._exceptions = _parse_config(self.config.allowed_direct_imports)
        return self._exceptions

    def visit_module(self, node):
        self._imports_to_check = {}

    @utils.check_messages('import-direct-attributes')
    def visit_attribute(self, node):

        if not isinstance(node.expr, astroid.nodes.Name):
            return
        name = node.expr.name
        if name not in self._imports_to_check:
            return
        module_name = self._imports_to_check[name]
        if (module_name, node.attrname) in self.exceptions:
            self.add_message(
                'import-direct-attributes',
                node=node,
                args=(node.attrname, module_name))

    def visit_import(self, node):
        for (name, alias) in node.names:
            if name in (module for module, attribute in self.exceptions):
                self._imports_to_check[alias or name] = name

    @utils.check_messages('import-only-modules')
    def visit_importfrom(self, node):
        try:
            imported_module = node.do_import_module(node.modname)
        except astroid.AstroidBuildingException:
            # Import errors should be checked elsewhere.
            return

        if node.level is None:
            modname = node.modname
        else:
            modname = '.' * node.level + node.modname

        for (name, alias) in node.names:
            # Wildcard imports should be checked elsewhere.
            if name == '*':
                continue

            try:
                imported_module.import_module(name, True)
                # Good, we could import "name" as a module relative to the "imported_module".
                full_name = f'{modname}.{name}'
                if full_name in (module for module, attribute in self.exceptions):
                    self._imports_to_check[alias or name] = full_name
            except astroid.AstroidImportError:
                if (modname, name) in self.exceptions:
                    # The non-module import is one of the allowed ones.
                    continue
                self.add_message(
                    'import-only-modules',
                    node=node,
                    args=(name, modname),
                )
            except astroid.AstroidBuildingException:
                # Some other error.
                pass


def register(linter):
    linter.register_checker(ImportOnlyModulesChecked(linter))
