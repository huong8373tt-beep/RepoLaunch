from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from launch.core.platforms.windows import (
    DEFAULT_WINDOWS_DOCKER_HOST,
    WINDOWS_DOCKER_PIPE_TARGET,
    WindowsRuntime,
    build_windows_docker_mounts,
    get_windows_container_docker_pipe_source,
)


class WindowsDockerHostTests(unittest.TestCase):
    def test_native_pipe_is_selected_when_callers_do_not_set_docker_host(self) -> None:
        class FakeDocker:
            def __init__(self) -> None:
                self.pings = 0

            def from_env(self, **_kwargs):
                return self

            def ping(self) -> None:
                self.pings += 1

        fake_docker = FakeDocker()
        with patch.dict(os.environ, {}, clear=True), patch(
            "launch.core.platforms.windows.docker", fake_docker
        ), patch.object(
            WindowsRuntime,
            "pull_image",
            side_effect=RuntimeError("stop-after-ping"),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop-after-ping"):
                WindowsRuntime._start_container("image", "instance", 1, 1)
            self.assertEqual(os.environ["DOCKER_HOST"], DEFAULT_WINDOWS_DOCKER_HOST)
            self.assertEqual(fake_docker.pings, 1)

    def test_native_daemon_pipe_is_mounted_at_the_standard_guest_path(self) -> None:
        with patch.dict(os.environ, {"DOCKER_HOST": DEFAULT_WINDOWS_DOCKER_HOST}, clear=True):
            self.assertEqual(
                get_windows_container_docker_pipe_source(),
                r"\\.\pipe\docker_engine_windows",
            )
            mounts = build_windows_docker_mounts()
            self.assertEqual(len(mounts), 1)
            self.assertEqual(mounts[0]["Source"], r"\\.\pipe\docker_engine_windows")
            self.assertEqual(mounts[0]["Target"], WINDOWS_DOCKER_PIPE_TARGET)
            self.assertEqual(mounts[0]["Type"], "npipe")
        with patch.dict(os.environ, {"SWE_WINDOWS_CONTAINER_DOCKER_PIPE_SOURCE": ""}, clear=True):
            self.assertIsNone(get_windows_container_docker_pipe_source())
            self.assertEqual(build_windows_docker_mounts(), [])

    def test_explicit_docker_host_remains_authoritative(self) -> None:
        class FakeDocker:
            def from_env(self, **_kwargs):
                return self

            def ping(self) -> None:
                pass

        explicit = "npipe:////./pipe/custom_engine"
        with patch.dict(os.environ, {"DOCKER_HOST": explicit}, clear=True), patch(
            "launch.core.platforms.windows.docker", FakeDocker()
        ), patch.object(
            WindowsRuntime,
            "pull_image",
            side_effect=RuntimeError("stop-after-ping"),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop-after-ping"):
                WindowsRuntime._start_container("image", "instance", 1, 1)
            self.assertEqual(os.environ["DOCKER_HOST"], explicit)


if __name__ == "__main__":
    unittest.main()