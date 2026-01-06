#!/usr/bin/env python
# coding: utf-8

"""
Build utilities for pykit3 packages.
"""

import importlib.util
import sys


def load_parent_package():
    """
    Load the parent directory as a package module.

    Returns:
        tuple: (package_name, package_module)
    """
    import os

    parent_dir = os.path.dirname(os.path.dirname(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Read the __init__.py file to get the package name
    init_file = os.path.join(parent_dir, "__init__.py")
    package_name = None

    with open(init_file, "r") as f:
        for line in f:
            if line.strip().startswith("__name__"):
                # Extract package name from __name__ = "package_name"
                package_name = line.split("=")[1].strip().strip("\"'")
                break

    if not package_name:
        # Fallback: use directory name
        package_name = os.path.basename(parent_dir)

    # Load the module with proper package context using importlib
    spec = importlib.util.spec_from_file_location(package_name, init_file)
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = pkg  # Add to sys.modules so relative imports work
    spec.loader.exec_module(pkg)

    return package_name, pkg
