import importlib
import pytest

# 확인하고 싶은 라이브러리 리스트
required_packages = [
    "requests",
    "playwright",
    "dotenv"
]

@pytest.mark.parametrize("package_name", required_packages)
def test_package_installed(package_name):
    """라이브러리가 설치되어 있는지 확인"""
    spec = importlib.util.find_spec(package_name)
    assert spec is not None, f"{package_name} is not installed"
