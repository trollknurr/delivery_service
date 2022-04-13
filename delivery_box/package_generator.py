import logging
import multiprocessing
import random
import signal
import time
import uuid
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class PackingType(IntEnum):
    """How package will be packed"""

    ENVELOPE = 0
    BOX = 1
    TUBE = 2
    ROLL = 3


@dataclass
class Package:
    """Holds package params"""

    # Unique identifier of a package
    idx: uuid.UUID
    # Lenght, width, height in cm
    dimensions: tuple[int, int, int]
    # Weight in kg
    weight: float
    type: PackingType


class DeliveryGenerator:
    """
    Generates new packages for delivery
    """

    def __iter__(self) -> "DeliveryGenerator":
        return self

    def __next__(self) -> Package:
        while True:
            package_type = random.choice(list(PackingType))
            dimensions = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 10))
            weight = random.random() * 100
            package = Package(idx=uuid.uuid4(), dimensions=dimensions, weight=weight, type=package_type)
            return package


class PackageGeneratorWorker(multiprocessing.Process):
    """
    Collect packages and put them in queue for packing in boxes
    """

    def __init__(self, queue, exit_event, *args, delay=0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue
        self.exit_event = exit_event
        self.delay = delay

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        generator = DeliveryGenerator()
        while not self.exit_event.is_set():
            package = next(generator, None)
            if package is None:
                logger.warning("Generator exhausted, worker exited")
                break

            self.queue.put(package)
            time.sleep(self.delay)
