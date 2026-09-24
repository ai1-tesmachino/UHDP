import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    log_dir=Path("logs")
    log_dir.mkdir(exist_ok=True)
    handler=RotatingFileHandler(log_dir/"uhdp.log",maxBytes=10000000,backupCount=5)
    fmt=logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(fmt)
    console=logging.StreamHandler()
    console.setFormatter(fmt)
    root=logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
        root.addHandler(console)
