import asyncio

import pytest

from delivery_box.box_packer import PickupBox
from delivery_box.delivery_car import CarBrokenError, IncorrectAddressError, PickUpCar


@pytest.fixture(scope="module")
def pickup_car():
    return PickUpCar(idx=1, box_queue=asyncio.Queue(), result_queue=asyncio.Queue())


@pytest.mark.asyncio
async def test_car_broke(mocker, pickup_car):
    random_mock = mocker.patch("random.random", return_value=0.991)
    with pytest.raises(CarBrokenError):
        await pickup_car._deliver_package(mocker.Mock())
    random_mock.assert_called_once()


@pytest.mark.asyncio
async def test_incorrect_address(mocker, pickup_car):
    random_mock = mocker.patch("random.random", return_value=0.985)
    with pytest.raises(IncorrectAddressError):
        await pickup_car._deliver_package(mocker.Mock())
    random_mock.assert_called_once()


@pytest.mark.asyncio
async def test_successful_delivery(mocker, pickup_car):
    random_mock = mocker.patch("random.random", return_value=0.8)
    package_mock = mocker.Mock()
    package = await pickup_car._deliver_package(package_mock)
    random_mock.assert_called_once()
    assert package is package_mock


@pytest.mark.asyncio
async def test_box_deliver(mocker, pickup_car):
    mocker.patch("random.random", side_effect=[0.5, 0.985, 0.995])
    good, bad_address, redelivery = mocker.Mock(), mocker.Mock(), mocker.Mock()
    box = PickupBox([good, bad_address, redelivery])
    delivery_results = await pickup_car.deliver_box(box)
    assert len(delivery_results.delivered) == 1
    assert delivery_results.delivered[0] is good

    assert len(delivery_results.incorrect) == 1
    assert delivery_results.incorrect[0] is bad_address

    assert len(delivery_results.redelivery) == 1
    assert delivery_results.redelivery[0] is redelivery
