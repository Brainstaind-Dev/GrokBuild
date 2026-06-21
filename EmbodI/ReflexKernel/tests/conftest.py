"""Pytest configuration and shared fixtures for ReflexKernel tests."""

import pytest

from reflexkernel.config import load_config


@pytest.fixture(scope="session")
def sim_config():
    return load_config("configs/sim_only.yaml")


@pytest.fixture
def sim_only_config():
    return load_config("configs/sim_only.yaml")
