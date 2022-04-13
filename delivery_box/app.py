import asyncio
import logging
import multiprocessing
import queue
import threading
import time

from delivery_box.box_packer import BoxPackerWorker
from delivery_box.config import ServiceConfig
from delivery_box.delivery_car import CarDispatcher
from delivery_box.package_generator import (  # pylint: disable=W0611
    Package,
    PackageGeneratorWorker,
)

logger = logging.getLogger(__name__)


class App:
    """
    Controls whole delivery process
    """

    def __init__(self, config: ServiceConfig):
        self.config = config

        self.exit_event = multiprocessing.Event()
        self.package_queue: "multiprocessing.Queue[Package]" = multiprocessing.Queue()
        self.box_queue: "multiprocessing.Queue[Package]" = multiprocessing.Queue()

        self.successful_queue: "queue.Queue[Package]" = queue.Queue()
        self.error_queue: "queue.Queue[Package]" = queue.Queue()

        self.delivery_generator_workers = [
            PackageGeneratorWorker(
                queue=self.package_queue, exit_event=self.exit_event, delay=self.config.package_generator_delay
            )
            for _ in range(self.config.num_package_generators)
        ]
        logger.info("Starting with %d package generators", len(self.delivery_generator_workers))

        self.box_packer_workers = [
            BoxPackerWorker(
                package_queue=self.package_queue,
                box_queue=self.box_queue,
                exit_event=self.exit_event,
                packer_config=self.config.box_packer,
            )
            for _ in range(self.config.num_box_packers)
        ]
        logger.info("Starting with %d box packers", len(self.box_packer_workers))

        self.car_dispatcher = CarDispatcher(
            package_queue=self.package_queue,
            box_queue=self.box_queue,
            successful_queue=self.successful_queue,
            error_queue=self.error_queue,
            exit_event=self.exit_event,
            config=self.config,
        )
        self.dispatcher_thread = None
        self.result_log_thread = None

    def start(self):
        """
        Start worker processes and threads
        """
        logger.info("Starting app")
        for worker in self.delivery_generator_workers:
            worker.start()

        for worker in self.box_packer_workers:
            worker.start()

        self.dispatcher_thread = threading.Thread(
            name="CarDispatcherThread", target=lambda: asyncio.run(self.car_dispatcher.run())
        )
        self.dispatcher_thread.start()
        self.result_log_thread = threading.Thread(name="LogResultThread", target=self.log_delivery_results)
        self.result_log_thread.start()
        self.loop()

    def loop(self):
        """
        Keep an eye on service work, maybe export metrics for prometheus
        Note: qsize gives approximate size of queue
        """
        while not self.exit_event.is_set():
            logger.info("%d packages in queue", self.package_queue.qsize())
            logger.info("%d boxes in queue", self.box_queue.qsize())
            logger.info("%d successful delivery", self.successful_queue.qsize())
            logger.info("%d error delivery", self.error_queue.qsize())
            time.sleep(1)

    def log_delivery_results(self):
        """
        Log results of delivery process
        """
        successful_package_cnt = 0
        failed_package_cnt = 0
        log_time = time.perf_counter()
        while not self.exit_event.is_set():
            try:
                successful_package = self.successful_queue.get_nowait()  # pylint: disable=W0612
                # do some useful stuff, maybe log to db
            except queue.Empty:
                pass
            else:
                successful_package_cnt += 1

            try:
                failed_package = self.error_queue.get_nowait()  # pylint: disable=W0612
                # do some useful stuff, maybe log to db
            except queue.Empty:
                pass
            else:
                failed_package_cnt += 1

            delta = time.perf_counter() - log_time
            if delta >= 1.0:
                logger.info(
                    "%d successful deliveries, %d failed deliveries", successful_package_cnt, failed_package_cnt
                )
                log_time = time.perf_counter()

    def stop(self):
        """
        Stopping application, waiting for workers shutdown
        """
        logger.info("Stopping app")
        self.exit_event.set()
        logger.info("Delivery generator joining...")
        for worker in self.delivery_generator_workers:
            if worker.is_alive():
                worker.join()

        logger.info("Box packer joining...")
        for worker in self.box_packer_workers:
            if worker.is_alive():
                worker.join()

        logger.info("Car dispatcher joining...")
        if self.dispatcher_thread.is_alive():
            self.dispatcher_thread.join()

        logger.info("Result logger joining...")
        if self.result_log_thread.is_alive():
            self.result_log_thread.join()

        logger.info("App stopped")
