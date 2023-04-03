"""Utility functions for prettifying the tui"""
from rich import console, live
from rich.progress import Progress
from rich.logging import RichHandler
import logging
FORMAT = "%(message)s"
from rich.traceback import install
install()
r_console = console.Console()
r_print = r_console.print
r_progress = Progress(console=r_console, expand=True, transient=True)
r_stat = r_console.status("Starting... \n")
group = console.Group(
    r_progress,
    r_stat
)
r_wrapper = live.Live(group)
def setup(log_level=None):
    """sets up the environment for rich"""

    if not log_level:
        log_level = "INFO"
    logging.basicConfig(
        level=log_level, format=FORMAT,
        handlers=[RichHandler()]
    )
    r_logger = logging.getLogger("rich")
    
    return r_wrapper, r_print, r_console, r_stat, r_logger, r_progress
