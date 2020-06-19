from __future__ import print_function

import os
import platform
import sys
import click
from .init import init_command
from .run import run_command
from .prepare import prepare_command

root_path = os.path.dirname(__file__)


class NoAppException(click.UsageError):
    """Raised if an application cannot be found or loaded."""


def get_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    import werkzeug
    from .. import __version__

    message = "Python %(python)s\nMlChain %(mlchain)s\nWerkzeug %(werkzeug)s"
    click.echo(
        message
        % {
            "python": platform.python_version(),
            "mlchain": __version__,
            "werkzeug": werkzeug.__version__,
        },
        color=ctx.color,
    )
    ctx.exit()


version_option = click.Option(
    ["--version"],
    help="Show the flask version",
    expose_value=False,
    callback=get_version,
    is_flag=True,
    is_eager=True,
)


class AppGroup(click.Group):
    """This works similar to a regular click :class:`~click.Group` but it
    changes the behavior of the :meth:`command` decorator so that it
    automatically wraps the functions in :func:`with_appcontext`.
    Not to be confused with :class:`FlaskGroup`.
    """

    def command(self, *args, **kwargs):
        """This works exactly like the method of the same name on a regular
        :class:`click.Group` but it wraps callbacks in :func:`with_appcontext`
        unless it's disabled by passing ``with_appcontext=False``.
        """

        def decorator(f):
            return click.Group.command(self, *args, **kwargs)(f)

        return decorator

    def group(self, *args, **kwargs):
        """This works exactly like the method of the same name on a regular
        :class:`click.Group` but it defaults the group class to
        :class:`AppGroup`.
        """
        kwargs.setdefault("cls", AppGroup)
        return click.Group.group(self, *args, **kwargs)


class MLChainGroup(AppGroup):
    """Special subclass of the :class:`AppGroup` group that supports
    loading more commands from the configured Flask app.  Normally a
    developer does not have to interface with this class but there are
    some very advanced use cases for which it makes sense to create an
    instance of this.
    For information as of why this is useful see :ref:`custom-scripts`.
    :param add_default_commands: if this is True then the default run and
        shell commands will be added.
    :param add_version_option: adds the ``--version`` option.
    :param create_app: an optional callback that is passed the script info and
        returns the loaded app.
    :param load_dotenv: Load the nearest :file:`.env` and :file:`.flaskenv`
        files to set environment variables. Will also change the working
        directory to the directory containing the first file found.
    :param set_debug_flag: Set the app's debug flag based on the active
        environment
    .. versionchanged:: 1.0
        If installed, python-dotenv will be used to load environment variables
        from :file:`.env` and :file:`.flaskenv` files.
    """

    def __init__(
            self,
            add_default_commands=True,
            create_app=None,
            add_version_option=True,
            load_dotenv=True,
            set_debug_flag=True,
            **extra
    ):
        params = list(extra.pop("params", None) or ())

        if add_version_option:
            params.append(version_option)

        AppGroup.__init__(self, params=params, **extra)
        self.create_app = create_app
        self.load_dotenv = load_dotenv
        self.set_debug_flag = set_debug_flag

        if add_default_commands:
            self.add_command(run_command)
            self.add_command(init_command)
            self.add_command(prepare_command)

        self._loaded_plugin_commands = False

    def _load_plugin_commands(self):
        if self._loaded_plugin_commands:
            return
        try:
            import pkg_resources
        except ImportError:
            self._loaded_plugin_commands = True
            return

        for ep in pkg_resources.iter_entry_points("flask.commands"):
            self.add_command(ep.load(), ep.name)
        self._loaded_plugin_commands = True

    def get_command(self, ctx, name):
        self._load_plugin_commands()

        # We load built-in commands first as these should always be the
        # same no matter what the app does.  If the app does want to
        # override this it needs to make a custom instance of this group
        # and not attach the default commands.
        #
        # This also means that the script stays functional in case the
        # application completely fails.
        rv = AppGroup.get_command(self, ctx, name)
        if rv is not None:
            return rv

    def list_commands(self, ctx):
        self._load_plugin_commands()

        # The commands available is the list of both the application (if
        # available) plus the builtin commands.
        rv = set(click.Group.list_commands(self, ctx))
        return sorted(rv)

    def main(self, *args, **kwargs):
        # Set a global flag that indicates that we were invoked from the
        # command line interface. This is detected by Flask.run to make the
        # call into a no-op. This is necessary to avoid ugly errors when the
        # script that is loaded here also attempts to start a server.
        # path = sys.argv[1]

        return super(MLChainGroup, self).main(*args, **kwargs)


cli = MLChainGroup()


def main(as_module=False):
    cli.main(args=sys.argv[1:], prog_name="python -m mlchain" if as_module else None)


if __name__ == "__main__":
    main(as_module=True)
