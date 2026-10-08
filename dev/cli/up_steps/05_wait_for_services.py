"""Wait for infrastructure services to be healthy."""

import time

from shared import (
    SERVER_DIR,
    Context,
    console,
    print_output_tail,
    run_command,
    step_spinner,
    step_status,
)

NAME = "Waiting for services to be ready"


def wait_for_postgres(timeout: int = 60) -> bool:
    """Wait for PostgreSQL to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = run_command(
            ["docker", "compose", "exec", "-T", "db", "pg_isready", "-U", "outception"],
            cwd=SERVER_DIR,
            capture=True,
        )
        if result and result.returncode == 0:
            return True
        time.sleep(1)
    return False


def wait_for_redis(timeout: int = 60) -> bool:
    """Wait for Redis to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = run_command(
            ["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"],
            cwd=SERVER_DIR,
            capture=True,
        )
        if result and result.returncode == 0 and "PONG" in result.stdout:
            return True
        time.sleep(1)
    return False


def _report_service_timeout(label: str, service: str, timeout: int) -> None:
    step_status(False, label, f"not ready after {timeout}s")
    status = run_command(
        ["docker", "compose", "ps", "-a", service, "--format", "{{.Name}}: {{.Status}}"],
        cwd=SERVER_DIR,
        capture=True,
    )
    if status and status.stdout.strip():
        console.print(f"    [dim]{status.stdout.strip()}[/dim]")
    logs = run_command(
        ["docker", "compose", "logs", "--no-color", "--tail", "10", service],
        cwd=SERVER_DIR,
        capture=True,
    )
    console.print(f"  [bold]Last log lines from the {service} container:[/bold]")
    print_output_tail(logs, lines=10)
    console.print("  [bold]To fix:[/bold]")
    console.print(
        "    • A container that exited right away usually means server/.env is missing or incomplete:"
        " run [bold]./dev/setup-environment[/bold], then [bold]dev up[/bold] again"
    )
    console.print(
        f"    • Otherwise restart it with [bold]docker compose restart {service}[/bold] in server/"
        f" and check [bold]docker compose logs {service}[/bold]"
    )


def run(ctx: Context) -> bool:
    """Wait for PostgreSQL and Redis to be ready."""
    with step_spinner("Waiting for PostgreSQL..."):
        if wait_for_postgres(timeout=60):
            step_status(True, "PostgreSQL", "ready")
        else:
            _report_service_timeout("PostgreSQL", "db", 60)
            return False

    with step_spinner("Waiting for Redis..."):
        if wait_for_redis(timeout=60):
            step_status(True, "Redis", "ready")
        else:
            _report_service_timeout("Redis", "redis", 60)
            return False

    return True
