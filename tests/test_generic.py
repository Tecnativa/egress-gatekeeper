import time

import requests
from conftest import ComposeCommon
from python_on_whales import DockerClient


class TestGeneric(ComposeCommon):
    _template = "generic_test"
    _service = "main"
    _compose = "compose.yml"

    def test_web_conection(self, started_project: DockerClient):
        time.sleep(4)
        req = requests.get("http://localhost:8081")
        assert req.ok
