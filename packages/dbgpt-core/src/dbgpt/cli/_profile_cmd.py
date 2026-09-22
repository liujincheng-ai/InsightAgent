"""Profile management subcommands: list, show, create, switch, delete."""

import click


@click.group()
def profile():
    """Manage InsightAgent configuration profiles."""
    pass


@profile.command(name="list")
def profile_list():
    """List all configured profiles."""
    from dbgpt.cli._config import configs_dir, read_active_profile

    configs = configs_dir()
    active = read_active_profile()
    toml_files = sorted(configs.glob("*.toml"))

    if not toml_files:
        click.echo("No profiles configured. Run: dbgpt setup")
        return

    for f in toml_files:
        name = f.stem
        marker = "* " if name == active else "  "
        click.echo(f"{marker}{name}")


@profile.command()
@click.argument("name")
def show(name):
    """Show the TOML configuration for a profile."""
    from dbgpt.cli._config import profile_config_path

    path = profile_config_path(name)
    if not path.exists():
        raise click.ClickException(
            f"Profile '{name}' not found. Run: dbgpt profile create {name}"
        )
    click.echo(path.read_text(encoding="utf-8"))


@profile.command()
@click.argument("name")
def create(name):
    """Create or reconfigure a profile (runs the setup wizard)."""
    from dbgpt.cli._wizard import run_setup_wizard

    run_setup_wizard(pre_selected_profile=name)


@profile.command()
@click.argument("name")
def switch(name):
    """Set a profile as the active default."""
    from dbgpt.cli._config import profile_config_path, write_active_profile

    path = profile_config_path(name)
    if not path.exists():
        click.echo(
            f"Error: Profile '{name}' not found. Run: dbgpt profile create {name}",
            err=False,
        )
        raise SystemExit(1)
    write_active_profile(name)
    click.echo(f"Switched active profile to: {name}")


@profile.command()
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete(name, yes):
    """Delete a profile configuration file."""
    from dbgpt.cli._config import (
        profile_config_path,
        read_active_profile,
        write_active_profile,
    )

    path = profile_config_path(name)
    if not path.exists():
        raise click.ClickException(f"Profile '{name}' not found.")

    if not yes:
        click.confirm(f"Delete profile '{name}'?", abort=True)

    path.unlink()

    # Clear active pointer if this was the active profile
    if read_active_profile() == name:
        write_active_profile("")  # clear by writing empty string

    click.echo(f"Deleted profile: {name}")
