#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Ensure local pkgs folder is in sys.path
BASE_DIR = Path(__file__).resolve().parent
pkgs_dir = BASE_DIR / "pkgs"
if pkgs_dir.is_dir() and str(pkgs_dir) not in sys.path:
    sys.path.insert(0, str(pkgs_dir))


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Verify that it is available on your PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
