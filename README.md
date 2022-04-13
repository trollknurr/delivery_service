# Toy project modeling delivery service

## Build and run

Project build docker image and have some common things in Makefile.
Run project:

> make up

This will kick up service with default configs. If you want to use custom
config for service, build container & start shell:

> make build
> make shell

For configuration service uses Facebook Hydra. For overriding default values
use like this:

> python -m delivery_box ++num_package_generators=8 ++package_generator_delay=0.01

For overriding, for example, box packer config whole section

> python -m delivery_box box_packer=greedy ++num_package_generators=8

Or just override part

> python -m delivery_box ++box_packer.packages_in_box=100 ++num_package_generators=8

## Develop

Some useful commands, formatting:

> make format

Linting:

> make check

## What to work on

* Graceful shutdown, with processing all pending tasks without producing new one
* If Box packer can't get enough packages for queue he must return them back to packages queue and 
eventually one of Box packers will have enough packages