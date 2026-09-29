"""Ensure local AWS data and links cannot enter the submission ZIP."""

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import build, package


class PackageTests(unittest.TestCase):
    def test_lambda_zip_excludes_build_host_cli_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archives = []
            for host in ("one", "two"):
                source = root / host
                (source / "bin").mkdir(parents=True)
                (source / "sample.dist-info").mkdir()
                (source / "bin/cli").write_text("#!/host/" + host + "/python\n")
                (source / "sample.py").write_text("VALUE = 1\n")
                (source / "sample.dist-info/RECORD").write_text(
                    "bin/cli,host-specific-" + host + ",20\nsample.py,constant,10\n"
                )
                destination = root / (host + ".zip")
                build.write_archive(source, destination)
                archives.append(destination.read_bytes())
            self.assertEqual(*archives)

    def test_only_allowed_source_is_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "README.md").write_text("Source")
            (root / "terraform").mkdir()
            (root / "terraform/terraform.tfstate").write_text("local state")
            (root / "private.pem").write_text("local key")
            archive = root / "dist/source.zip"
            with patch.object(package, "SOURCE_FILES", ("README.md",)):
                package.build_archive(root, archive)
            with zipfile.ZipFile(archive) as contents:
                self.assertIsNone(contents.testzip())
                self.assertEqual(contents.namelist(), ["get-task2/README.md"])

    def test_linked_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "secret").write_text("local")
            (root / "README.md").symlink_to(root / "secret")
            with patch.object(package, "SOURCE_FILES", ("README.md",)):
                with self.assertRaisesRegex(ValueError, "linked source"):
                    package.build_archive(root, root / "source.zip")


if __name__ == "__main__":
    unittest.main()
