from conftest import ComposeCommon
from python_on_whales import DockerClient


class DoodbaCommon(ComposeCommon):
    _template = "doodba_test"
    _service = "odoo"
    _dbname = None

    @classmethod
    def pre_start(cls, docker_client: DockerClient, project):
        super().pre_start(docker_client, project)
        docker_client.compose.run(
            service="odoo",
            command=["click-odoo-dropdb", cls._dbname, "--if-exists"],
            remove=True,
        )
        docker_client.compose.run(
            service="odoo",
            command=["click-odoo-initdb", "--no-demo", "-n", cls._dbname, "-m", "base"],
            remove=True,
        )


class TestTest(DoodbaCommon):
    _compose = "test.yml"
    _dbname = "prod"


class TestDevel(DoodbaCommon):
    _compose = "devel.yml"
    _dbname = "devel"

    @classmethod
    def pre_start(cls, docker_client: DockerClient, project):
        auto = project / "odoo" / "auto"
        addons = auto / "addons"
        addons.mkdir(parents=True, exist_ok=True)
        auto.chmod(0o777)
        addons.chmod(0o777)
        (project / "odoo" / "custom" / "src").chmod(0o777)
        docker_client.compose.run(service="devel-setup", remove=True)
        super().pre_start(docker_client, project)
