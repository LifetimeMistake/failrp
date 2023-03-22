from os.path import exists, abspath, join, dirname
import os
import hashlib
from shutil import copy
from rich import print as rprint
from rich.progress import track, Progress
from rpfile_parse import RPFileParser
from utils import parse_arguments

RPFILE = abspath("./")
REPO = "/home/prfl/Downloads"
CACHE = "/home/prfl/cache"
DEST = "/home/prfl/dest"

if not (exists(REPO) and exists(DEST)):
    rprint("ERROR Repository and Destination fs not mounted")
    exit(1)

rich_progress = Progress()

def check_cache(file):
    """Validates if cache has the same file as in the remote"""
    if exists(join(CACHE, file)):
        cache_hash = get_hash(join(CACHE, file))
        if exists(join(REPO, f"{file}.sha256")):
            rprint("Reading", join(REPO, f"{file}.sha256"))
            with open(join(REPO, f"{file}.sha256"), "r", encoding="utf-8") as repo_hash:
                if repo_hash.read() == cache_hash:
                    rprint('[green]SUCCESS[/green]: Validated ')
                    return True
                else:
                    rprint('[yellow]WARN[/yellow]: Cache checksum mismatch')
                return False
        else:
            rprint('[yellow]WARN[/yellow]: Cant check file, file hash not in repo')
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
        rprint('Reading', f'{file}.sha256')
        with open(f"{file}.sha256", "r", encoding="utf-8") as _f:
            checksum = _f.read()
    else:
        rprint(f'generating hash for {file}')
        sha256_hash = hashlib.sha256()
        with open(file, "rb") as _f:
            for byte_block in track(iter(lambda: _f.read(4096),b"")):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()
        with open(f"{file}.sha256", "w", encoding="utf-8") as f_w:
            rprint(f'saving {file}.sha256')
            f_w.write(checksum)
    return checksum

def _deploy(_from, _to):
    rprint(f"DEPLOYING FROM {_from} TO {_to}")

def _copy(_from, _to):
    if exists(CACHE):
        if not check_cache(_from):
            rprint(f"COPYING FROM {join(REPO, _from)} TO {join(CACHE, _from)}")
            copy(join(REPO, _from), join(CACHE, _from))
            try:
                copy(join(REPO, f"{_from}.sha256"), join(CACHE, f"{_from}.sha256"))
            except:
                __h = get_hash(join(CACHE, _from))
                rprint(f"Hash of file {join(REPO, _from)}: {__h}")
        os.makedirs(dirname(join(DEST, to_relative(_to))), exist_ok=True)
        rprint(f"COPYING FROM {join(CACHE, _from)} TO {join(DEST, to_relative(_to))}")
        copy(join(CACHE, _from), join(DEST, to_relative(_to)))
    else:
        os.makedirs(dirname(join(DEST, to_relative(_to))), exist_ok=True)
        rprint(
            f"COPYING FROM {join(REPO, _from)} TO {join(DEST, to_relative(_to))}")
        copy(join(REPO, _from), join(DEST, to_relative(_to)))

def _unpack(_from, _to):
    rprint(f"UNPACKING FROM {_from} TO {_to}")

def _pull(_from, _to):
    rprint(f"PULLING FROM {_from} TO {_to}")

def _ignore(*args):
    rprint(f"IGNORING {', '.join(args)}")

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
