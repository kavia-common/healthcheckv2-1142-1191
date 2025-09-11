"""
Alias package for backward-compatible imports.

This package serves as a thin wrapper around the new 'healthcheckv2' package so that
legacy imports like:
    from healthcheck.healthcheck import ...
continue to work without modifying existing code/tests.

It exposes:
- 'healthcheck' submodule, which re-exports from 'healthcheckv2.healthcheck'
"""

# Re-export the contents from healthcheckv2.healthcheck at the package level
from healthcheckv2.healthcheck import *  # noqa: F401,F403

# Expose a 'healthcheck' submodule so dotted imports work:
#    from healthcheck.healthcheck import XYZ
# This maps to healthcheckv2.healthcheck
from types import ModuleType
import sys as _sys
import importlib as _importlib

# Import the real module
_real_healthcheck = _importlib.import_module("healthcheckv2.healthcheck")

# Insert alias into sys.modules under 'healthcheck.healthcheck'
_sys.modules.setdefault("healthcheck.healthcheck", _real_healthcheck)

# Also make it available as an attribute for 'import healthcheck.healthcheck'
healthcheck: ModuleType = _real_healthcheck  # type: ignore

__all__ = getattr(_real_healthcheck, "__all__", [])  # best-effort to mirror
