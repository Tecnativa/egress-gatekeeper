from shutil import copytree

import pytest
from python_on_whales import DockerClient, DockerException, docker

fail_hosts = [
    "https://github.com",
    "https://gitlab.com",
]
allow_hosts = [
    "https://www.tecnativa.com",
    "https://1.1.1.1",
]
param_array = [(x, False) for x in fail_hosts] + [(x, True) for x in allow_hosts]


def pytest_addoption(parser):
    """Allow prebuilding image for local testing."""
    parser.addoption(
        "--prebuild",
        action="store_true",
        default=True,
        help="Build local image before testing",
    )
    parser.addoption(
        "--image",
        action="store",
        default="tecnativa/egress-gatekeeper:testonly",
        help="Specify testing image name",
    )
    parser.addoption(
        "--tmp",
        action="store",
        default=False,
        help="RUn tests in /tmp isntead of project folder",
    )


@pytest.fixture(scope="session")
def image(request, pytestconfig):
    """Builds image if needed."""
    image_name = request.config.getoption("--image")
    if request.config.getoption("--prebuild"):
        return docker.build(
            tags=image_name, context_path=pytestconfig.rootdir, load=True
        )
    return docker.image.inspect(image_name)


@pytest.fixture(scope="function")
def compose_project():
    docker = DockerClient(
        compose_files="tests/compose.yaml",
    )
    yield docker
    docker.compose.down(remove_orphans=True)


class ComposeCommon:
    _template = None
    _compose = None
    _service = None

    @pytest.fixture(scope="class")
    @classmethod
    def project(cls, tmp_path_factory, request):
        template = request.config.rootpath / "tests" / cls._template
        if not request.config.getoption("--tmp"):
            return template
        tmp_dir = tmp_path_factory.mktemp("project")
        project = tmp_dir / cls._template
        copytree(template, project)
        return project

    @pytest.fixture(scope="class")
    @classmethod
    def docker_client(cls, project):
        yield DockerClient(
            compose_files=str(project / cls._compose),
        )

    @classmethod
    def pre_start(cls, docker_client: DockerClient, project):
        docker_client.compose.pull(quiet=True, ignore_pull_failures=True)
        docker_client.compose.down(remove_orphans=True, volumes=True)
        docker_client.compose.build()

    @pytest.fixture(scope="class")
    @classmethod
    def started_project(cls, docker_client: DockerClient, project):
        cls.pre_start(docker_client, project)
        docker_client.compose.up(detach=True, wait=True)
        yield docker_client
        docker_client.compose.down(remove_orphans=True, volumes=True)

    @pytest.mark.parametrize("url,allow", param_array)
    def test_allowed_hosts_comopose_exec(
        self, started_project: DockerClient, url, allow
    ):
        if not allow:
            with pytest.raises(DockerException) as exc:
                started_project.compose.execute(self._service, self.curl_cmd(url))
            assert exc.value.return_code in [6, 7]
        else:
            started_project.compose.execute(self._service, self.curl_cmd(url))

    @pytest.mark.parametrize("url,allow", param_array)
    def test_allowed_hosts_compose_run(self, docker_client: DockerClient, url, allow):
        if not allow:
            with pytest.raises(DockerException) as exc:
                docker_client.compose.run(
                    self._service,
                    command=self.curl_args(url),
                    entrypoint="curl",
                    remove=True,
                )
            assert exc.value.return_code in [6, 7]
        else:
            docker_client.compose.run(
                self._service,
                command=self.curl_args(url),
                entrypoint="curl",
                remove=True,
            )

    def curl_cmd(self, url):
        return ["curl"] + self.curl_args(url)

    def curl_args(self, url):
        return [
            "-o",
            "/dev/null",
            "--fail",
            "--silent",
            "--show-error",
            "--connect-timeout",
            "2",
            url,
        ]
