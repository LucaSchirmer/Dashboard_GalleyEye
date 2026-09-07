from pathlib import Path
import shutil
import pytest
from galleyeye.data import load_data

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def bundle(): return load_data(ROOT/"data")

@pytest.fixture
def data_copy(tmp_path):
    target=tmp_path/"data"
    shutil.copytree(ROOT/"data",target)
    return target
