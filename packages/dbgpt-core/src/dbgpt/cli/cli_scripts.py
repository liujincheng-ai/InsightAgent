import copy
import logging

import click

logging.basicConfig(
    level=logging.WARNING,
    encoding="utf-8",
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("dbgpt_cli")


@click.group()
@click.option(
    "--log-level",
    required=False,
    type=str,
    default="warn",
    help="Log level",
)
@click.version_option()
def cli(log_level: str):
    logger.setLevel(logging.getLevelName(log_level.upper()))


def add_command_alias(command, name: str, hidden: bool = False, parent_group=None):
    if not parent_group:
        parent_group = cli
    new_command = copy.deepcopy(command)
    new_command.hidden = hidden
    parent_group.add_command(new_command, name=name)


@click.group(invoke_without_command=True)
@click.pass_context
def start(ctx):
    """Start specific server."""
    if ctx.invoked_subcommand is None:
        # Try web first, then webserver as fallback
        cmd = start.commands.get("web") or start.commands.get("webserver")
        if cmd:
            ctx.invoke(cmd)
        else:
            click.echo(ctx.get_help())


@click.group()
def stop():
    """Start specific server."""
    pass


@click.group()
def install():
    """Install dependencies, plugins, etc."""
    pass


@click.group()
def db():
    """Manage your metadata database and your datasources."""
    pass


@click.group()
def new():
    """New a template."""
    pass


@click.group()
def app():
    """Manage your apps(dbgpts)."""
    pass


@click.group()
def repo():
    """The repository to install the dbgpts from."""
    pass


@click.group()
def run():
    """Run your dbgpts."""
    pass


@click.group()
def net():
    """Net tools."""
    pass


@click.group()
def tool():
    """InsightAgent Tools."""


# ---------------------------------------------------------------------------
# dbgpt setup
# ---------------------------------------------------------------------------


@click.command(name="setup")
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default=None,
    help=(
        "Provider profile to configure: openai / kimi / qwen / minimax / "
        "deepseek / ollama.  If omitted, an interactive menu is shown."
    ),
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Non-interactive: skip wizard and use defaults / env variables.",
)
@click.option(
    "--api-key",
    type=str,
    required=False,
    default=None,
    envvar="DBGPT_API_KEY",
    help="API key for the chosen provider.",
)
@click.option(
    "--show",
    is_flag=True,
    default=False,
    help="Show the current active profile and config path, then exit.",
)
def setup_command(profile: str, yes: bool, api_key: str, show: bool):
    """Configure InsightAgent's LLM provider and write ~/.dbgpt/configs/<profile>.toml.

    Run without arguments for an interactive wizard, or use --yes for
    non-interactive / CI usage.

    \b
    Examples:
      dbgpt setup                          # interactive wizard
      dbgpt setup --profile openai --yes  # use OPENAI_API_KEY from env
      dbgpt setup --profile kimi --api-key sk-xxx
      dbgpt setup --show                   # print current config
    """
    try:
        from dbgpt.cli._config import (
            profile_config_path,
            read_active_profile,
        )
        from dbgpt.cli._wizard import run_setup_noninteractive, run_setup_wizard
        from dbgpt.util.console.console import CliLogger

        cl = CliLogger()

        if show:
            active = read_active_profile()
            if active:
                path = profile_config_path(active)
                cl.info(f"Active profile : [bold]{active}[/bold]")
                cl.info(f"Config file    : {path}")
                if not path.exists():
                    cl.warning("  ⚠ Config file does not exist yet. Run `dbgpt setup`.")
            else:
                cl.warning("No profile configured yet. Run `dbgpt setup`.")
            return

        if yes:
            run_setup_noninteractive(
                profile_name=profile or "openai",
                api_key=api_key,
            )
        else:
            run_setup_wizard(
                pre_selected_profile=profile,
                pre_set_key=api_key,
            )

    except ImportError as e:
        logger.warning(f"Setup wizard unavailable: {e}")
        raise click.ClickException(str(e))


# ---------------------------------------------------------------------------
# Stop all
# ---------------------------------------------------------------------------

stop_all_func_list = []


@click.command(name="all")
def stop_all():
    """Stop all servers"""
    for stop_func in stop_all_func_list:
        stop_func()


@click.command(name="none")
def start_none():
    """Start InsightAgent in API-only mode (no web UI). [Planned]"""
    click.echo(
        "API-only mode (no web UI) is planned for a future release.\n"
        "For now, use: dbgpt start web"
    )


start.add_command(start_none)

cli.add_command(start)
cli.add_command(stop)
# cli.add_command(install)
cli.add_command(db)
cli.add_command(new)
cli.add_command(app)
cli.add_command(repo)
cli.add_command(run)
cli.add_command(net)
cli.add_command(tool)
cli.add_command(setup_command)
from dbgpt.cli._profile_cmd import profile as profile_cmd  # noqa: E402

cli.add_command(profile_cmd, name="profile")
add_command_alias(stop_all, name="all", parent_group=stop)

try:
    from dbgpt.model.cli import (
        _stop_all_model_server,
        model_cli_group,
        start_apiserver,
        start_model_controller,
        start_model_worker,
        stop_apiserver,
        stop_model_controller,
        stop_model_worker,
    )

    add_command_alias(model_cli_group, name="model", parent_group=cli)
    add_command_alias(start_model_controller, name="controller", parent_group=start)
    add_command_alias(start_model_worker, name="worker", parent_group=start)
    add_command_alias(start_apiserver, name="apiserver", parent_group=start)

    add_command_alias(stop_model_controller, name="controller", parent_group=stop)
    add_command_alias(stop_model_worker, name="worker", parent_group=stop)
    add_command_alias(stop_apiserver, name="apiserver", parent_group=stop)
    stop_all_func_list.append(_stop_all_model_server)

except ImportError as e:
    logging.warning(f"Integrating dbgpt model command line tool failed: {e}")

try:
    from dbgpt_app._cli import (
        _stop_all_dbgpt_server,
        migration,
        start_webserver,
        stop_webserver,
    )

    add_command_alias(start_webserver, name="webserver", parent_group=start)
    add_command_alias(start_webserver, name="web", parent_group=start)
    add_command_alias(stop_webserver, name="webserver", parent_group=stop)
    # Add migration command
    add_command_alias(migration, name="migration", parent_group=db)
    stop_all_func_list.append(_stop_all_dbgpt_server)

except ImportError as e:
    logging.warning(f"Integrating dbgpt webserver command line tool failed: {e}")

try:
    from dbgpt_app.knowledge._cli.knowledge_cli import knowledge_cli_group

    add_command_alias(knowledge_cli_group, name="knowledge", parent_group=cli)
except ImportError as e:
    logging.warning(f"Integrating dbgpt knowledge command line tool failed: {e}")


try:
    from dbgpt.util.tracer.tracer_cli import trace_cli_group

    add_command_alias(trace_cli_group, name="trace", parent_group=cli)
except ImportError as e:
    logging.warning(f"Integrating dbgpt trace command line tool failed: {e}")

try:
    from dbgpt_serve.utils.cli import serve

    add_command_alias(serve, name="serve", parent_group=new)
except ImportError as e:
    logging.warning(f"Integrating dbgpt serve command line tool failed: {e}")


try:
    from dbgpt.util.cli.flow_compat import tool_flow_cli_group
    from dbgpt.util.dbgpts.cli import (
        add_repo,
        list_installed_apps,
        list_repos,
        new_dbgpts,
        reinstall,
        remove_repo,
        update_repo,
    )
    from dbgpt.util.dbgpts.cli import install as app_install
    from dbgpt.util.dbgpts.cli import list_all_apps as app_list_remote
    from dbgpt.util.dbgpts.cli import uninstall as app_uninstall

    add_command_alias(list_repos, name="list", parent_group=repo)
    add_command_alias(add_repo, name="add", parent_group=repo)
    add_command_alias(remove_repo, name="remove", parent_group=repo)
    add_command_alias(update_repo, name="update", parent_group=repo)
    add_command_alias(app_install, name="install", parent_group=app)
    add_command_alias(app_uninstall, name="uninstall", parent_group=app)
    add_command_alias(reinstall, name="reinstall", parent_group=app)
    add_command_alias(app_list_remote, name="list-remote", parent_group=app)
    add_command_alias(list_installed_apps, name="list", parent_group=app)
    add_command_alias(new_dbgpts, name="app", parent_group=new)
    add_command_alias(tool_flow_cli_group, name="flow", parent_group=tool)

except ImportError as e:
    logging.warning(f"Integrating dbgpt dbgpts command line tool failed: {e}")

try:
    from dbgpt_client._cli import flow as run_flow

    add_command_alias(run_flow, name="flow", parent_group=run)
except ImportError as e:
    logging.warning(f"Integrating dbgpt client command line tool failed: {e}")

try:
    from dbgpt.util.network._cli import start_forward

    add_command_alias(start_forward, name="forward", parent_group=net)
except ImportError as e:
    logging.warning(f"Integrating dbgpt net command line tool failed: {e}")


def main():
    return cli()


if __name__ == "__main__":
    main()
