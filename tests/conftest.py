import time

import pytest
import ray


@pytest.fixture(autouse=True, scope="function")
def clean_ray_between_tests():
    if ray.is_initialized():
        ray.shutdown()

    yield

    if ray.is_initialized():
        ray.shutdown()

    time.sleep(0.1)  # tiny pause helps Ray daemons exit cleanly
