from dataclasses import dataclass

from hydra.core.config_store import ConfigStore


@dataclass
class BoxPackerConfig:
    """
    Settings for box packer
    """

    extra_packages: float = 0.2
    packages_in_box: int = 64
    return_packages_to_queue: bool = True


@dataclass
class ServiceConfig:
    """
    Settings for whole service
    """

    box_packer: BoxPackerConfig

    num_package_generators: int = 4
    package_generator_delay: float = 0.1

    num_box_packers: int = 1

    num_pickup_cars: int = 2


cs = ConfigStore.instance()
cs.store(name="base_config", node=ServiceConfig)
