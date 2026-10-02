"""Exercise Make with isolated files and command doubles, never live AWS tools."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "1" if (ROOT / "bootstrap").is_dir() else "2"


class MakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="make lab ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(ROOT / "Makefile", self.root / "Makefile")
        (self.root / "terraform").mkdir()
        (self.root / "terraform/terraform.tfvars.example").write_text("example\n")
        self.log = self.root / "commands.jsonl"
        tool = self.root / "command double"
        tool.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, sys\n"
            "with open(os.environ['COMMAND_LOG'], 'a') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        )
        tool.chmod(0o755)
        self.env = dict(
            os.environ, TERRAFORM=str(tool), PYTHON=str(tool), COMMAND_LOG=str(self.log)
        )
        # Do not inherit recursive make options or the host's local configuration.
        for name in (
            "MAKEFLAGS",
            "MFLAGS",
            "MAKELEVEL",
            "PLAN",
            "DESTROY_PLAN",
            "REFRESH_PLAN",
            "UNPROTECT_PLAN",
            "PAUSE_PLAN",
            "RESUME_PLAN",
            "SSH_KEY",
        ):
            self.env.pop(name, None)

    def make(self, *args, **env):
        return subprocess.run(
            ["make", "--no-print-directory", *args],
            cwd=self.root,
            env=dict(self.env, **env),
            text=True,
            capture_output=True,
            check=True,
        )

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_default_only_displays_help(self):
        result = self.make()
        self.assertIn("destroy-plan", result.stdout)
        self.assertIn("verify", result.stdout)
        self.assertFalse(self.log.exists())

    def test_apply_and_destroy_only_apply_the_saved_plan_without_building_or_replanning(self):
        self.make(
            "apply", "destroy", PLAN="reviewed plan.tfplan", DESTROY_PLAN="delete plan.tfplan"
        )
        self.assertEqual(
            self.commands(),
            [
                ["-chdir=terraform", "apply", "reviewed plan.tfplan"],
                ["-chdir=terraform", "apply", "delete plan.tfplan"],
            ],
        )

    def test_plans_include_teardown_protection_and_build_happens_before_task2_plan(self):
        self.make("plan", "destroy-plan", PLAN="review plan.tfplan")
        expected = [["-chdir=terraform", "plan", "-out=review plan.tfplan"]]
        destroy = ["-chdir=terraform", "plan", "-destroy"]
        if TASK == "1":
            destroy.append("-var=deletion_protection=false")
        else:
            expected.insert(0, ["scripts/build.py"])
        expected.append(destroy + ["-out=destroy.tfplan"])
        self.assertEqual(self.commands(), expected)

    def test_setup_and_clean_preserve_state_configuration_and_evidence(self):
        self.make("setup")
        config = self.root / "terraform/terraform.tfvars"
        config.write_text("my configuration\n")
        self.make("setup")
        protected = [
            "terraform/terraform.tfstate",
            "terraform/terraform.tfstate.backup",
            "evidence/result.json",
            "terraform/.terraform/lock",
            "terraform/custom.tfplan",
        ]
        for name in protected:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("preserve")
        plan = self.root / ("terraform/task" + TASK + ".tfplan")
        plan.write_text("generated")
        self.make("clean", PYTHON=sys.executable)
        self.assertFalse(plan.exists())
        self.assertEqual(config.read_text(), "my configuration\n")
        for name in protected:
            self.assertEqual((self.root / name).read_text(), "preserve")

    def test_live_wrapper_arguments_and_sequential_verify(self):
        if TASK == "1":
            key = self.root / "private key"
            key.write_text("test placeholder")
            self.make("verify", "failover", SSH_KEY=str(key))
            self.assertEqual(
                self.commands(),
                [
                    ["scripts/task1.py", "verify", "--key", str(key)],
                    ["scripts/task1.py", "failover", "--key", str(key), "--execute"],
                ],
            )
        else:
            self.make("-j8", "verify", "demo-schedule", SINCE="20m", DELAY="240")
            self.assertEqual(
                self.commands(),
                [
                    ["scripts/task2.py", "status"],
                    ["scripts/task2.py", "invoke"],
                    ["scripts/task2.py", "logs", "--since", "20m"],
                    ["scripts/task2.py", "demo-create", "--delay", "240"],
                ],
            )


if __name__ == "__main__":
    unittest.main()
