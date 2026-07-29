"""Configure the GitHub integration."""

import typer

from shared import (
    ROOT_DIR,
    SECRETS_FILE,
    Context,
    console,
    run_command,
    step_status,
)

NAME = "Configuring GitHub integration"


def is_github_configured() -> bool:
    """Check if GitHub App is configured."""
    if SECRETS_FILE.exists():
        content = SECRETS_FILE.read_text()
        if "OUTCEPTION_GITHUB_CLIENT_ID=" in content:
            for line in content.split("\n"):
                if line.startswith("OUTCEPTION_GITHUB_CLIENT_ID="):
                    value = line.split("=", 1)[1].strip().strip("\"'")
                    return bool(value)
    return False


def is_github_skipped() -> bool:
    """Check if user chose to skip GitHub setup."""
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().split("\n"):
            if line.startswith("OUTCEPTION_SKIP_GITHUB_SETUP="):
                value = line.split("=", 1)[1].strip().strip("\"'")
                return value.lower() == "true"
    return False


def set_github_skipped(skipped: bool = True) -> None:
    """Remember that user chose to skip GitHub setup."""
    _update_secrets_file("OUTCEPTION_SKIP_GITHUB_SETUP", "true" if skipped else None)


def _update_secrets_file(key: str, value: str | None) -> None:
    """Update a key in the secrets file."""
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().split("\n"):
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip().strip("\"'")

    if value is None:
        existing.pop(key, None)
    else:
        existing[key] = value

    with open(SECRETS_FILE, "w") as f:
        f.write("# Outception Development Secrets\n")
        f.write("# Shared across Git worktrees\n\n")
        for k, v in existing.items():
            delimiter = "'" if '"' in v else '"'
            f.write(f"{k}={delimiter}{v}{delimiter}\n")


def run(ctx: Context) -> bool:
    """Configure the GitHub integration."""
    if ctx.skip_integrations:
        return True

    # Reset skip flags on clean
    if ctx.clean:
        set_github_skipped(False)

    # GitHub
    if is_github_configured():
        step_status(True, "GitHub App", "configured")
    elif is_github_skipped():
        step_status(True, "GitHub App", "skipped (run with --clean to reconfigure)")
    else:
        console.print(
            "\n  [dim]GitHub App enables login with GitHub and repository integrations.[/dim]"
        )
        console.print(
            "  [dim]You can skip this and still develop most features without it.[/dim]\n"
        )
        if typer.confirm("  Set up GitHub App now?", default=False):
            console.print("\n  [bold]GitHub App Setup[/bold]\n")
            console.print("  [bold]Step 1:[/bold] Start ngrok to get an external URL")
            console.print("    Run in another terminal: [bold]ngrok http 8000[/bold]")
            console.print(
                "    Get ngrok at: [link=https://ngrok.com]https://ngrok.com[/link]\n"
            )

            external_url = typer.prompt(
                "  Enter your ngrok URL (e.g., https://abc123.ngrok.dev)"
            )

            console.print(
                "\n  [bold]Step 2:[/bold] Your browser will open to create a GitHub App"
            )
            console.print("    Just click through - all settings are pre-configured!\n")

            setup_args = [
                str(ROOT_DIR / "dev" / "setup-environment"),
                "--setup-github-app",
                "--backend-external-url",
                external_url,
            ]
            result = run_command(setup_args, capture=False)
            if result and result.returncode == 0:
                step_status(True, "GitHub App", "configured")
                set_github_skipped(False)
            else:
                step_status(False, "GitHub App", "setup failed")
        else:
            if typer.confirm("  Remember this choice?", default=True):
                set_github_skipped(True)
                step_status(True, "GitHub App", "skipped (remembered)")
            else:
                step_status(True, "GitHub App", "skipped (will ask again next time)")

    return True
