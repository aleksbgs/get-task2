#!/usr/bin/env python3
"""Build a deterministic Lambda ZIP with hash-locked Python dependencies."""

import csv
import hashlib
import io
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_archive(package, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob("*")):
            relative = path.relative_to(package)
            # Wheel CLI launchers embed the build host's interpreter path.
            if (
                not path.is_file()
                or relative.parts[0] == "bin"
                or "__pycache__" in path.parts
                or path.suffix == ".pyc"
            ):
                continue
            data = path.read_bytes()
            if path.name == "RECORD" and path.parent.name.endswith(".dist-info"):
                rows = csv.reader(io.StringIO(data.decode()))
                record = io.StringIO()
                csv.writer(record, lineterminator="\n").writerows(
                    row for row in rows if not row[0].startswith("bin/")
                )
                data = record.getvalue().encode()
            info = zipfile.ZipInfo(relative.as_posix(), (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def main():
    destination = ROOT / "build/lambda.zip"
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python-version",
                "3.14",
                "--python-platform",
                "aarch64-manylinux2014",
                "--only-binary",
                ":all:",
                "--require-hashes",
                "--no-compile",
                "--target",
                str(package),
                "--requirements",
                str(ROOT / "requirements.txt"),
            ],
            check=True,
        )
        (package / "handler.py").write_bytes((ROOT / "src/handler.py").read_bytes())
        write_archive(package, destination)
    print(destination)
    print("SHA-256:", hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
