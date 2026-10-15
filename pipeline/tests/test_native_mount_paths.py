import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.attribution import all_fail_problems
from pipeline.benchmark import offline_docker
from pipeline.benchmark.harness_docker import HarnessDockerEnvironment


class NativeMountPathTests(unittest.TestCase):
    def test_colon_containing_trial_source_is_not_parsed_as_a_mount_mode(self):
        source = "/campaign/source:1/trial/agent"
        self.assertEqual(offline_docker.unambiguous_bind_mount(source + ":/logs/agent:rw"), {
            "type": "bind", "source": source, "target": "/logs/agent", "read_only": False,
            "bind": {"create_host_path": False}})

    def test_readonly_source_with_multiple_colons_stays_readonly(self):
        source = "/campaign/source:1/version:2/fixture"
        mount = offline_docker.unambiguous_bind_mount(source + ":/app/environment/files:ro")
        self.assertEqual(mount["source"], source)
        self.assertEqual(mount["target"], "/app/environment/files")
        self.assertTrue(mount["read_only"])

    def test_default_writable_bind_and_space_containing_paths_are_preserved(self):
        mount = offline_docker.unambiguous_bind_mount("/campaign/a task:1/log:/logs/agent")
        self.assertEqual(mount["source"], "/campaign/a task:1/log")
        self.assertFalse(mount["read_only"])

    def test_existing_long_syntax_and_named_volumes_are_not_reinterpreted(self):
        long_mount = {"type": "bind", "source": "/fixture", "target": "/data", "read_only": True}
        for mount in (long_mount, "named-volume:/data:ro", "named-volume"):
            self.assertEqual(offline_docker.unambiguous_bind_mount(mount), mount)

    def test_compose_cannot_fall_back_to_legacy_bind_strings_for_a_colon_path(self):
        original = {"type": "bind", "source": "/source:1/logs", "target": "/logs", "read_only": True,
                    "bind": {"create_host_path": True, "propagation": "rprivate"}}
        fixed = offline_docker.unambiguous_bind_mount(original)
        self.assertFalse(fixed["bind"]["create_host_path"])
        self.assertEqual(fixed["bind"]["propagation"], "rprivate")
        self.assertTrue(fixed["read_only"])
        self.assertTrue(original["bind"]["create_host_path"])

    def test_both_network_providers_use_the_corrected_mount_writer(self):
        self.assertIs(HarnessDockerEnvironment._write_mounts_compose_file,
                      offline_docker.OfflineDockerEnvironment._write_mounts_compose_file)

    def test_compose_writer_preserves_other_services_and_explicit_mount_options(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mounts.json"
            volume = {"type": "bind", "source": "/safe", "target": "/data",
                      "read_only": True, "bind": {"propagation": "rprivate"}}
            original = {"services": {"main": {"volumes": ["/source:1/log:/logs:rw", volume]},
                                     "sidecar": {"network_mode": "none"}}}
            path.write_text(json.dumps(original))
            environment = offline_docker.OfflineDockerEnvironment.__new__(offline_docker.OfflineDockerEnvironment)
            with patch.object(offline_docker.DockerEnvironment, "_write_mounts_compose_file", return_value=path, create=True):
                self.assertEqual(environment._write_mounts_compose_file(), path)
            updated = json.loads(path.read_text())
            self.assertEqual(updated["services"]["main"]["volumes"][0]["source"], "/source:1/log")
            self.assertEqual(updated["services"]["main"]["volumes"][1], volume)
            self.assertEqual(updated["services"]["sidecar"], original["services"]["sidecar"])

    def test_void_only_measurement_does_not_suggest_altering_task_dependencies(self):
        with patch("pipeline.author.contracts.strict_json") as read:
            self.assertEqual(all_fail_problems(Path("unused"), {"trials": [], "by_step": {}}), [])
        read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
