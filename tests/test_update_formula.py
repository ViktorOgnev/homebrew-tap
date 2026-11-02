import copy
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "updater", Path(__file__).resolve().parents[1] / "scripts/update_formula.py"
)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class UpdateTests(unittest.TestCase):
    def source(self, version="1.2.3"):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name in (
                "LICENSE",
                "js/document-yjs/package-lock.json",
                "js/document-yjs/build.mjs",
            ):
                content = b"MIT License\n" if name == "LICENSE" else b"source"
                member = tarfile.TarInfo(f"kaiten_cli-{version}/{name}")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        data = stream.getvalue()
        source = {
            "packagetype": "sdist",
            "yanked": False,
            "filename": f"kaiten_cli-{version}.tar.gz",
            "url": f"https://files.pythonhosted.org/kaiten_cli-{version}.tar.gz",
            "digests": {"sha256": hashlib.sha256(data).hexdigest()},
        }
        return data, source

    def test_version_order_and_invalid_versions(self):
        self.assertGreater(
            updater.version_tuple("0.10.0"), updater.version_tuple("0.9.9")
        )
        for invalid in (
            "1.2.3rc1",
            "v1.2.3",
            "01.2.3",
            "١.٢.٣",
            "1.2.3\n",
            "1.2.3;exit",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                updater.version_tuple(invalid)

    def test_latest_ignores_prerelease_and_yanked_source(self):
        _, source = self.source()
        yanked = dict(source, yanked=True)
        payload = {
            "releases": {
                "0.9.0": [source],
                "0.10.0": [source],
                "1.0.0rc1": [source],
                "2.0.0": [yanked],
            }
        }
        self.assertEqual(updater.select_version(payload, None), "0.10.0")

    def test_metadata_fails_closed(self):
        data, source = self.source()
        valid = {
            "info": {"version": "1.2.3", "license_expression": "MIT"},
            "urls": [source],
        }
        self.assertEqual(updater.sdist_metadata(valid, "1.2.3"), source)
        updater.verify_source(data, source, "1.2.3")
        for field, value in (
            ("url", "https://evil.example/package.tar.gz"),
            ("yanked", True),
            ("filename", "other-package.tar.gz"),
        ):
            payload = copy.deepcopy(valid)
            payload["urls"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                updater.sdist_metadata(payload, "1.2.3")
        with self.assertRaises(ValueError):
            updater.sdist_metadata(valid, "1.2.4")
        valid["info"]["license_expression"] = None
        with self.assertRaises(ValueError):
            updater.sdist_metadata(valid, "1.2.3")

    def test_checksum_and_missing_sources_rejected(self):
        data, source = self.source()
        with self.assertRaises(ValueError):
            updater.verify_source(data + b"changed", source, "1.2.3")
        with self.assertRaises(KeyError):
            updater.verify_source(data, source, "1.2.4")

    def test_replacement_leaves_dependency_resources_untouched(self):
        text = (
            '  url "https://files.pythonhosted.org/kaiten_cli-0.3.5.tar.gz"\n  sha256 "'
            + "0" * 64
            + '"\n'
        )
        resources = (
            '\n  resource "click" do\n    url "https://example.com/click.tar.gz"\n    sha256 "'
            + "1" * 64
            + '"\n  end\n'
        )
        _, source = self.source()
        changed = updater.replace_source(text + resources, source)
        self.assertTrue(changed.endswith(resources))
        self.assertEqual(updater.current_version(changed), "1.2.3")

    def test_noop_downgrade_and_failed_regeneration_preserve_formula(self):
        data, source = self.source()
        original = (
            '  url "https://files.pythonhosted.org/kaiten_cli-1.2.3.tar.gz"\n  sha256 "'
            + "0" * 64
            + '"\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            formula = Path(directory) / "formula.rb"
            formula.write_text(original)
            with (
                patch.object(updater, "FORMULA", formula),
                patch.object(updater, "get_json") as fetch,
            ):
                fetch.return_value = {"releases": {"1.2.3": [source]}}
                updater.update(None)
                self.assertEqual(fetch.call_count, 1)
                with self.assertRaises(ValueError):
                    updater.update("1.2.2")
                fetch.return_value = {
                    "info": {"version": "1.2.3", "license_expression": "MIT"},
                    "urls": [source],
                }
                with (
                    patch.object(updater, "urlopen", return_value=io.BytesIO(data)),
                    patch.object(
                        updater.subprocess,
                        "run",
                        side_effect=RuntimeError("resolver failed"),
                    ),
                    self.assertRaises(RuntimeError),
                ):
                    updater.update("1.2.3", bootstrap=True)
                self.assertEqual(formula.read_text(), original)


if __name__ == "__main__":
    unittest.main()
