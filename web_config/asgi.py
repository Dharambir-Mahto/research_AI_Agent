import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
pkgs_dir = BASE_DIR / "pkgs"
if pkgs_dir.is_dir() and str(pkgs_dir) not in sys.path:
    sys.path.insert(0, str(pkgs_dir))

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_config.settings")

application = get_asgi_application()
