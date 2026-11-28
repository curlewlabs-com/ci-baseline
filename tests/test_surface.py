"""Verify the imports documented for consumers of the configuration readers.

An internal rename can update every caller in this checkout while leaving
those imports broken.
"""

import unittest

from ci_baseline_pyright.config import (
    RUFF_CONFIGURATIONS,
    ConfigError,
    own_configuration,
    python_floor,
    python_platform,
)


class TestSurface(unittest.TestCase):
    def test_documented_config_readers_are_importable(self) -> None:
        for reader in (
            RUFF_CONFIGURATIONS,
            ConfigError,
            own_configuration,
            python_floor,
            python_platform,
        ):
            self.assertIsNotNone(reader)
