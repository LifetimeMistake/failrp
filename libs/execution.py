from __future__ import annotations
from abc import abstractmethod, ABC
import os
import re
import sys
from rich.progress import Progress
import os.path as path
import tempfile
import shutil
from .pretty_copy import copy_with_callback
from .parsing import format_ocs, parse_output_string
from .rpfile import RPFile, DeployInstruction, PullInstruction, \
    CopyInstruction, UnpackInstruction, FormatInstruction
from .formatting import get_supported_filesystems, format_partition
from .repositories import ImageRepository
from .volumes import VolumeManager
from .imaging import deploy_image
from .constants import COPY_BLOCK_SIZE
from .pretty import setup as r_setup
from sh import mount, umount

wrapper, print, console, status, logger, progress = r_setup()

class Operation(ABC):
    """Generic Operation Class"""

    @abstractmethod
    def execute(self):
        """executes operation"""

class DeployOperation(Operation):
    """Operation Class For Deploying a image"""
    def __init__(self, executor: RPFileExecutor, instruction: DeployInstruction):
        image = executor.image_repo.get(instruction.image)
        source_volume = instruction.image_volume
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        if not destination:
            raise NameError(f"Deploy destination '{instruction.volume}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Deploy destination '{instruction.volume}' \
                                    unavailable on this system")

        self.image = image
        self.source_volume = source_volume
        self.target_part = destination.target

    def execute(self):
        status.update(f"Deploying {self.image.name} to {self.target_part.path}...")
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")
        logger.info(f"Using {self.image.best_path}")
        def _logger(typ: str):
            def choose_output(out):
                parsed_out = parse_output_string(format_ocs(out))
                if parsed_out:
                    if parsed_out[2] == 100:
                        status.update("Cleaning up")
                        return None
                    status.update(f"Remaining: {parsed_out[1]}, Rate: {parsed_out[3]} GB/Min, Progress: {parsed_out[2]}%")
                else:
                    logger.info(out)
            def hook(*args, **kw):
                try:
                    {"err": choose_output, 
                    "out": logger.info, 
                    "in": lambda x : x}[typ](*args, **kw)
                except:
                    pass
            return hook
        deploy_image(self.image, self.target_part, self.source_volume, io=_logger)


class PullOperation(Operation):
    """OperationClass for pulling a repository to device"""
    def __init__(self, executor: RPFileExecutor, instruction: PullInstruction):
        image = executor.image_repo.get(instruction.image)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        self.executor = executor
        self.image_name = image.name

    def execute(self):
        status.update(f"Pulling {self.image_name}...")
        # Get image blacklist
        blacklist = []
        for _op in self.executor.executed_operations:
            if isinstance(_op, PullOperation):
                blacklist.append(_op.image_name)

        task = progress.add_task(f"Pulling {self.image_name}...")

        try:
            self.executor.image_repo.pull(self.image_name, disallowed_deletions=blacklist, 
            progress_callback=lambda copied, copied_total, total: progress.update(task, completed=copied_total, total=total))
        except IOError:
            logger.warning("Cannot pull image, Insufficient space!")
        progress.remove_task(task)

class CopyOperation(Operation):
    """Operation Class for copying a file to device"""
    def __init__(self, executor: RPFileExecutor, instruction: CopyInstruction):
        image = executor.image_repo.get(instruction.image)
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        if not destination:
            raise NameError(f"Deploy destination '{instruction.volume}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{instruction.volume}' \
                                    unavailable on this system")

        self.image = image
        self.target_part = destination.target
        self.destination_path = instruction.path

    def execute(self):
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")

        mount_path = tempfile.mkdtemp()
        logger.info(f"Mounting {self.target_part.path} at {mount_path}")
        mount(self.target_part.path, mount_path)

        try:
            volume_path = self.destination_path.lstrip('/')
            destination_path = path.join(mount_path, volume_path)
            destination_dir = path.dirname(destination_path)
            if not path.isdir(destination_dir):
                raise FileNotFoundError(f"Path '/{path.dirname(volume_path)}' \
                                        does not exist in the target volume.")
            status.update(f"Copying {self.image.name} to {destination_path}...")
            logger.info(f"Using {self.image.best_path}")

            task = progress.add_task(f"Copying {self.image.name} to {destination_path}...")

            copy_with_callback(
                self.image.best_path, 
                destination_path, 
                callback=lambda copied, copied_total, total: progress.update(task, completed=copied_total, total=total),
                follow_symlinks=False,
                buffer_size=COPY_BLOCK_SIZE)

            progress.remove_task(task)
        finally:
            umount(mount_path)
            os.rmdir(mount_path)
            logger.info("Unmounted working volume")

class UnpackOperation(Operation):
    """Operation Class for Unzipping archives to device"""
    def __init__(self, executor: RPFileExecutor, instruction: CopyInstruction):
        image = executor.image_repo.get(instruction.image)
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        ext = f".{'.'.join(path.basename(image.best_path).split('.')[1:])}"
        supported_exts = []
        for _type, exts, _name in shutil.get_unpack_formats():
            supported_exts.extend(exts)

        if ext not in supported_exts:
            raise NotImplementedError(f"Image archive format '{ext}' not supported. \
                                      Supported formats: '{', '.join(supported_exts)}'")

        if not destination:
            raise NameError(f"Deploy destination '{instruction.volume}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{instruction.volume}' \
                                    unavailable on this system")

        self.image = image
        self.target_part = destination.target
        self.destination_path = instruction.path

    def execute(self):
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")

        mount_path = tempfile.mkdtemp()
        logger.info(f"Mounting {self.target_part.path} at {mount_path}")
        mount(self.target_part.path, mount_path)

        try:
            volume_path = self.destination_path.lstrip('/')
            destination_path = path.join(mount_path, volume_path)
            destination_dir = path.dirname(destination_path)
            if not path.isdir(destination_dir):
                raise FileNotFoundError(f"Path '/{path.dirname(volume_path)}' \
                                        does not exist in the target volume.")

            status.update(f"Unpacking {self.image.name} to {destination_path}...")
            logger.info(f"Using {self.image.best_path}")
            shutil.unpack_archive(self.image.best_path, destination_path)
        finally:
            umount(mount_path)
            os.rmdir(mount_path)
            logger.info("Unmounted working volume")

class FormatOperation(Operation):
    """Operation Class for Formatting a partition on device"""
    def __init__(self, executor: RPFileExecutor, instruction: FormatInstruction):
        fstype = instruction.fstype
        destination = executor.volume_man.get(instruction.volume)

        supported_filesystems = get_supported_filesystems()
        if fstype not in get_supported_filesystems():
            raise ValueError(f"Unsupported filesystem provided: '{fstype}', \
                             supported filesystems: '{', '.join(supported_filesystems)}")

        if not destination:
            raise NameError(f"Format target '{instruction.volume}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{instruction.volume}' \
                                    is unavailable on this system")

        self.fstype = fstype
        self.target_part = destination.target

    def execute(self):
        status.update(f"Formatting {self.target_part.path} to {self.fstype}...")
        format_partition(self.target_part, self.fstype, verbose=True)

class RPFileExecutor:
    """RPFile execution class"""
    def __init__(self, rpfile: RPFile, image_repo: ImageRepository, volume_man: VolumeManager):
        self.rpfile = rpfile
        self.image_repo = image_repo
        self.volume_man = volume_man
        self.operations = None
        self.executed_operations = None

    def compile(self, skip_unsupported=True):
        """Only God knows what happens here"""
        operations = []
        instructions = self.rpfile.instructions

        logger.info("Starting build")
        for i, instruction in enumerate(instructions):
            print(f"[{i+1}/{len(instructions)}] {instruction}")
            try:
                # YandereDev Coding momentos
                if isinstance(instruction, DeployInstruction):
                    operation = DeployOperation(self, instruction)
                elif isinstance(instruction, PullInstruction):
                    operation = PullOperation(self, instruction)
                elif isinstance(instruction, CopyInstruction):
                    operation = CopyOperation(self, instruction)
                elif isinstance(instruction, UnpackInstruction):
                    operation = UnpackOperation(self, instruction)
                elif isinstance(instruction, FormatInstruction):
                    operation = FormatOperation(self, instruction)
                else:
                    if skip_unsupported:
                        logger.warning(f"Skipping unsupported instruction type: {type(instruction)}")
                        continue
                    else:
                        raise (f"Unsupported instruction type: {type(instruction)}")
            except Exception as ex:
                raise RuntimeError("Build failed!") from ex

            operations.append(operation)

        self.operations = operations

    def execute(self):
        """Executes RPFile"""
        print("Starting execution")
        self.executed_operations = []

        if not self.operations:
            raise RuntimeError("Executor was not compiled! \
                               Use .compile() to build an operation list.")

        task = progress.add_task("Warming up....", total=len(self.operations))
        for i, _op in enumerate(self.operations):
            progress.update(task, completed=len(self.executed_operations), total=len(self.operations), description=f"Executing operation {i+1} of {len(self.operations)}: {type(_op).__name__}")
            try:
                _op.execute()
            except Exception as ex:
                raise RuntimeError("Execution failed!") from ex

            self.executed_operations.append(_op)

        print("Done executing RPFile")
        self.executed_operations.clear()
