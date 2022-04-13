import logging

import hydra

from delivery_box.app import App
from delivery_box.config import ServiceConfig

logger = logging.getLogger(__name__)


@hydra.main(config_path="../config", config_name="config")
def main(service_config: ServiceConfig):
    """
    Start app
    """
    app = App(service_config)

    try:
        app.start()
    except KeyboardInterrupt:
        logger.info("Got exit signal")
    finally:
        app.stop()


if __name__ == "__main__":
    main()  # pylint: disable=E1120
