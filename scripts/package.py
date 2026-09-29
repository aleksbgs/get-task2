#!/usr/bin/env python3
"""Package source only; deployment state, dependencies and evidence stay local."""

import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    ".gitattributes",
    ".gitignore",
    "Makefile",
    "README.md",
    "ruff.toml",
    "requirements.in",
    "requirements.txt",
    "src/handler.py",
    "scripts/build.py",
    "scripts/package.py",
    "terraform/.terraform.lock.hcl",
    "terraform/versions.tf",
    "terraform/variables.tf",
    "terraform/lambda.tf",
    "terraform/scheduler.tf",
    "terraform/sns.tf",
    "terraform/iam.tf",
    "terraform/monitoring.tf",
    "terraform/outputs.tf",
    "terraform/terraform.tfvars.example",
    "terraform/tests/plan.tftest.hcl",
    "tests/test_handler.py",
    "tests/test_package.py",
    "docs/DEMO_SR.md",
)


def build_archive(root, destination):
    root = root.resolve()
    files = []
    for name in SOURCE_FILES:
        path = root / name
        if path.resolve() != path or not path.is_file():
            raise ValueError("Missing or linked source: " + name)
        data = path.read_bytes()
        if re.search(
            rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
            data,
        ):
            raise ValueError("Potential credential: " + name)
        files.append(("get-task2/" + name, data))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(name, data)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(digest + "  " + destination.name + "\n")
    return len(files)


def main():
    destination = ROOT / "dist/GET-Task2-Lambda.zip"
    count = build_archive(ROOT, destination)
    print(destination)
    print("Included source files:", count)


if __name__ == "__main__":
    main()
