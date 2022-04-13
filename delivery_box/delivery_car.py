import asyncio
import logging
import multiprocessing
import queue
import random
from dataclasses import dataclass
from multiprocessing.synchronize import Event as _EventType
from typing import List

from delivery_box.box_packer import PickupBox
from delivery_box.config import ServiceConfig
from delivery_box.exceptions import CarBrokenError, IncorrectAddressError
from delivery_box.package_generator import Package

logger = logging.getLogger(__name__)


@dataclass
class CarDeliveryResult:
    """
    Hold results for one car delivery routine
    """

    delivered: List[Package]
    redelivery: List[Package]
    incorrect: List[Package]


class PickUpCar:
    """
    A car can only pickup a box of packages and the driver will deliver them one by one
    """

    def __init__(self, idx: int, box_queue: asyncio.Queue, result_queue: asyncio.Queue):
        self.idx = idx
        self.box_queue = box_queue
        self.result_queue = result_queue

    async def worker(self):
        """
        Represent driver work, where he delivers box, log results, and take new delivery
        """
        while True:
            pickup_box = await self.box_queue.get()
            result = await self.deliver_box(pickup_box)
            self.box_queue.task_done()
            await self.result_queue.put(result)

    async def deliver_box(self, pickup_box: PickupBox) -> CarDeliveryResult:
        """
        Deliver box of packages
        :param pickup_box: box of packages to deliver
        :return: dataclass representing results of car delivery session
        """
        result = CarDeliveryResult([], [], [])
        car_broken = False
        for package in pickup_box.packages:
            if car_broken:
                result.redelivery.append(package)
                continue

            try:
                await self._deliver_package(package)
            except IncorrectAddressError:
                result.incorrect.append(package)
                logger.warning("Incorrect address for package %s", package.idx)
            except CarBrokenError:
                result.redelivery.append(package)
                logger.warning("Car %s broken", self.idx)
                car_broken = True
            else:
                result.delivered.append(package)
        return result

    async def _deliver_package(self, package: Package) -> Package:
        """
        Deliver one package
        :param package: package to deliver
        :return: package if the delivery was successful
        :raises:
            - CarBrokenError
            - IncorrectAddressError
        """
        rnd = random.random()
        match rnd:
            case rnd if rnd > 0.99:
                raise CarBrokenError()
            case rnd if 0.98 < rnd <= 0.99:
                raise IncorrectAddressError()
            case _:
                await asyncio.sleep(0.01)

        return package


class CarDispatcher:
    """
    Bridge between sync and async parts of application
    Represent controller for cars
    """

    def __init__(
        self,
        config: ServiceConfig,
        box_queue: multiprocessing.Queue,
        package_queue: multiprocessing.Queue,
        successful_queue: queue.Queue,
        error_queue: queue.Queue,
        exit_event: _EventType,
    ):
        self.box_queue = box_queue
        self.package_queue = package_queue
        self.successful_queue = successful_queue
        self.error_queue = error_queue

        self.aio_box_queue: "asyncio.Queue[Package]" = asyncio.Queue()
        self.aio_result_queue: "asyncio.Queue[CarDeliveryResult]" = asyncio.Queue()

        self.exit_event = exit_event
        self.config = config
        self.cars = [
            PickUpCar(idx=i, box_queue=self.aio_box_queue, result_queue=self.aio_result_queue)
            for i in range(self.config.num_pickup_cars)
        ]

    async def run(self):
        """
        Collect new boxes to be delivered by cars, unpack delivery results, reschedule packages for delivery
        """
        car_worker_tasks = []
        for car in self.cars:
            car_worker_tasks.append(asyncio.create_task(car.worker()))
        logger.info("Car workers started")

        while not self.exit_event.is_set():
            try:
                box = self.box_queue.get_nowait()
            except queue.Empty:
                logger.debug("No new boxes for delivery")
            else:
                await self.aio_box_queue.put(box)

            try:
                result = self.aio_result_queue.get_nowait()
            except asyncio.QueueEmpty:
                logger.debug("No new results")
            else:
                for package in result.delivered:
                    self.successful_queue.put_nowait(package)

                await asyncio.sleep(0.01)
                for package in result.incorrect:
                    self.error_queue.put_nowait(package)

                await asyncio.sleep(0.01)
                for package in result.redelivery:
                    self.package_queue.put_nowait(package)

            logger.debug("Internal box queue: %s", self.aio_box_queue.qsize())
            await asyncio.sleep(0.01)

        logger.info("Car workers stopping")
        for car_task in car_worker_tasks:
            car_task.cancel()
        await asyncio.gather(*car_worker_tasks, return_exceptions=True)
        logger.info("CarDispatcher done")
