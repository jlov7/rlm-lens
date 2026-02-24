from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(frozen=True)
class EnvironmentStatus:
    docker_installed: bool
    docker_running: bool


def get_environment_status() -> EnvironmentStatus:
    docker_path = shutil.which("docker")
    if docker_path is None:
        return EnvironmentStatus(docker_installed=False, docker_running=False)

    try:
        subprocess.run(
            [docker_path, "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return EnvironmentStatus(docker_installed=True, docker_running=True)
    except (OSError, subprocess.SubprocessError):
        return EnvironmentStatus(docker_installed=True, docker_running=False)
