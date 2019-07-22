# From https://gist.github.com/jobevers/49432f6751753cfffea3cd2cddaaa183
# Credit to mitar on stackoverflow: https://stackoverflow.com/a/45390670/2752242

import astroid
from pylint import checkers, interfaces
from pylint.checkers import utils


class ImportOnlyModulesChecked(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker

    name = 'import-only-modules'
    priority = -1
    msgs = {
        'W5521': (
            "Import \"%s\" from \"%s\" is not a module.",
            'import-only-modules',
            "Only modules should be imported.",
        ),
    }

    options = (
        (
            'allowed-direct-imports',
            dict(
                metavar='module1.import1,module2.import2',
                default='',
                help='A comma-separated list of exceptions.'
            )
        ),
    )

    @utils.check_messages('import-only-modules')
    def visit_importfrom(self, node):
        try:
            imported_module = node.do_import_module(node.modname)
        except astroid.AstroidBuildingException:
            # Import errors should be checked elsewhere.
            return

        allowed_imports = self.config.allowed_direct_imports.split(',')

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
            except astroid.AstroidImportError:
                if f'{modname}.{name}' in allowed_imports:
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
