from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(*, level: str, log_path: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear existing handlers (helpful for repeated runs)
    for h in list(root.handlers):
        root.removeHandler(h)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

