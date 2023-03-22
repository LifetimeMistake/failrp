from os.path import exists, abspath, join, dirname
import os
import hashlib
from shutil import copy
from zipfile import ZipFile
from rich import console, live
from rich.progress import track, Progress
from rpfile_parse import RPFileParser
from utils import parse_arguments
import functools


r_console = console.Console()
r_print = r_console.print
r_progress = Progress(console=r_console, expand=True, transient=True)
r_stat = r_console.status("Syncing...")

group = console.Group(
    r_progress,
    r_stat
)

RPFILE = abspath("./")
REPO = "/home/prfl/Downloads"
CACHE = "/home/prfl/cache"
DEST = "/home/prfl/dest"

if not (exists(REPO) and exists(DEST)):
    r_print("ERROR Repository and Destination fs not mounted")
    exit(1)



def check_cache(file):
    """Validates if cache has the same file as in the remote"""
    if exists(join(CACHE, file)):
        cache_hash = get_hash(join(CACHE, file))
        if exists(join(REPO, f"{file}.sha256")):
            r_print("Reading", join(REPO, f"{file}.sha256"))
            with open(join(REPO, f"{file}.sha256"), "r", encoding="utf-8") as repo_hash:
                if repo_hash.read() == cache_hash:
                    r_print('[green]SUCCESS[/green]: Validated ')
                    return True
                else:
                    r_print('[yellow]WARN[/yellow]: Cache checksum mismatch')
                return False
        else:
            r_print('[yellow]WARN[/yellow]: Cant check file, file hash not in repo')
            return False
    return False

def to_relative(path: str):
    """Converts a absolute path to a relative path"""
    if path[0] in ["/", "\\"]:
        return path[1:]
    else:
        return path

def get_hash(file: str):
    """Creates and returns persistent hash of a file"""
    checksum = ""
    if exists(f"{file}.sha256"):
        r_print('Reading', f'{file}.sha256')
        with open(f"{file}.sha256", "r", encoding="utf-8") as _f:
            checksum = _f.read()
    else:
        r_print(f'generating hash for {file}')
        sha256_hash = hashlib.sha256()
        with open(file, "rb") as _f:
            track_hash = r_progress.add_task("Hashing", total=None)
            for byte_block in iter(lambda: _f.read(4096), b""):
                sha256_hash.update(byte_block)
            r_progress.remove_task(track_hash)
        checksum = sha256_hash.hexdigest()
        with open(f"{file}.sha256", "w", encoding="utf-8") as f_w:
            r_print(f'saving {file}.sha256')
            f_w.write(checksum)
    return checksum

def _deploy(_from, _to):
    r_print(f"DEPLOYING FROM {_from} TO {_to}")


def with_cache(func):
    @functools.wraps(func)
    def wrapper_decorator(_from, _to):
        # stat = console.status("Syncing...")
        with live.Live(group):
            if exists(CACHE):
                if not check_cache(_from):
                    r_stat.update(
                        f"COPYING FROM {join(REPO, _from)} TO {join(CACHE, _from)}")
                    copy(join(REPO, _from), join(CACHE, _from))
                    try:
                        copy(join(REPO, f"{_from}.sha256"),
                            join(CACHE, f"{_from}.sha256"))
                    except:
                        __h = get_hash(join(CACHE, _from))
                        r_print(f"Hash of file {join(REPO, _from)}: {__h}")
                func(_from, _to, True, status=r_stat)
            else:
                func(_from, _to, False, status=r_stat)
                # Do something after
    return wrapper_decorator

@with_cache
def _copy(_from, _to, cached, status):
    if cached:
        os.makedirs(dirname(join(DEST, to_relative(_to))), exist_ok=True)
        status.update(f"COPYING FROM {join(CACHE, _from)} TO {join(DEST, to_relative(_to))}")
        copy(join(CACHE, _from), join(DEST, to_relative(_to)))
    else:
        os.makedirs(dirname(join(DEST, to_relative(_to))), exist_ok=True)
        status.update(
            f"COPYING FROM {join(REPO, _from)} TO {join(DEST, to_relative(_to))}")
        copy(join(REPO, _from), join(DEST, to_relative(_to)))

@with_cache
def _unpack(_from, _to, cached, status):
    if cached:
        os.makedirs(dirname(join(DEST, to_relative(_to))), exist_ok=True)
        status.update(
            f"UNPACKING FROM {join(CACHE, _from)} TO {join(DEST, to_relative(_to))}")
        with ZipFile(file=join(CACHE, _from)) as zip_file:
            track_unzip = r_progress.add_task(
                total=len(zip_file.namelist()), description=f"UNZIPPING: {join(CACHE, _from)}")
            for file in zip_file.namelist():
                zip_file.extract(member=file, path=join(DEST, to_relative(_to)))
                r_progress.advance(track_unzip)
            r_progress.remove_task(track_unzip)

    else:
        status.update(
            f"UNPACKING FROM {join(REPO, _from)} TO {join(DEST, to_relative(_to))}")
        with ZipFile(file=join(REPO, _from)) as zip_file:
            track_unzip = r_progress.add_task(
                total=len(zip_file.namelist()), description=f"UNZIPPING: {join(REPO, _from)}")
            for file in zip_file.namelist():
                zip_file.extract(member=file, path=join(
                    DEST, to_relative(_to)))
                r_progress.advance(track_unzip)
            r_progress.remove_task(track_unzip)
            
# status.update(f"UNPACKING FROM {_from} TO {_to}")

def _pull(_from, _to):
    r_print(f"PULLING FROM {_from} TO {_to}")

def _ignore(*args):
    r_print(f"IGNORING {', '.join(args)}")

INSTRUCTIONS = {
    "DEPLOY": _deploy,
    "COPY": _copy,
    "PULL": _pull,
    "UNPACK": _unpack
}

def _exec_commands(_rp: RPFileParser):
    for step in _rp.structure:
        params = parse_arguments(step["value"])
        INSTRUCTIONS.get(step["instruction"], _ignore)(*params)

rp_file = RPFileParser(RPFILE)
commands = rp_file.structure

_exec_commands(rp_file)
