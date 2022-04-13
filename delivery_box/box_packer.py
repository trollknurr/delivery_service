import logging
import multiprocessing
import queue
import random
import signal
from multiprocessing.synchronize import Event as _EventType
from typing import List, Tuple

from delivery_box.config import BoxPackerConfig
from delivery_box.package_generator import Package

logger = logging.getLogger(__name__)


class PickupBox:
    """
    Represents a box of packages to deliver
    """

    max_packages = 64

    def __init__(self, packages: list[Package]):
        if len(packages) > self.max_packages:
            raise ValueError(f"Too many packages for pick up: {len(packages)}")

        self.__packages = packages

    def __len__(self) -> int:
        return len(self.__packages)

    @property
    def packages(self) -> list[Package]:  # pylint: disable=C0116
        return self.__packages


class BoxPackerWorker(multiprocessing.Process):
    """
    Service for packing packages in boxes
    """

    def __init__(
        self,
        package_queue: multiprocessing.Queue,
        box_queue: multiprocessing.Queue,
        exit_event: _EventType,
        packer_config: BoxPackerConfig,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.package_queue = package_queue
        self.box_queue = box_queue
        self.exit_event = exit_event

        self.packer_config = packer_config

    @property
    def packages_to_pull(self):
        """
        Placeholder for sophisticated logic of how much packages take from pending
        """
        return PickupBox.max_packages + (PickupBox.max_packages * self.packer_config.extra_packages)

    def run(self):
        """
        Take some packages, efficient pack them with algorithm and queue for delivery
        """
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        extra_packages = None

        while not self.exit_event.is_set():
            package_buffer = []
            if extra_packages:
                package_buffer.extend(extra_packages)

            while not self.exit_event.is_set() and len(package_buffer) < self.packages_to_pull:
                try:
                    package = self.package_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                else:
                    package_buffer.append(package)

            logger.debug("Fullfilled package buffer, starting to pack")
            box, extra_packages = self.pack_to_box(package_buffer)

            if extra_packages and self.packer_config.return_packages_to_queue:
                for package in extra_packages:
                    self.package_queue.put_nowait(package)
                extra_packages = None

            self.box_queue.put_nowait(box)
            logger.debug("Box successfully packed")

    def pack_to_box(self, package_buffer: List[Package]) -> Tuple[PickupBox, List[Package]]:
        """
        Sophisticated algorithm for optimal 3D packing packages in box
        """
        random.shuffle(package_buffer)
        return PickupBox(package_buffer[: PickupBox.max_packages]), package_buffer[PickupBox.max_packages :]
