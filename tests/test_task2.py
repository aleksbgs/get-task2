"""Live-command boundary tests; no AWS credentials or requests are needed."""

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import task2

OUT = {
    "region": "eu-central-1",
    "function_arn": "arn:aws:lambda:eu-central-1:123456789012:function:get-task2-hello",
    "scheduler_role_arn": "arn:aws:iam::123456789012:role/get-task2-scheduler",
    "schedule_group": "get-task2",
    "schedule_name": "get-task2-daily-0100",
}


class LiveCommandTests(unittest.TestCase):
    def test_empty_state_fails_before_any_aws_command(self):
        with patch.object(task2, "run") as run:
            run.return_value.stdout = "{}"
            with self.assertRaisesRegex(ValueError, "Deploy this project first"):
                task2.outputs()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][-2:], ["output", "-json"])

    def test_wrong_account_is_rejected(self):
        with patch.object(task2, "aws", return_value={"Account": "999999999999"}):
            with self.assertRaisesRegex(ValueError, "different account"):
                task2.check_identity(OUT)

    def test_aws_commands_use_the_deployment_region(self):
        self.assertEqual(
            task2.aws_command(OUT, "sts", "get-caller-identity"),
            [
                "aws",
                "--region",
                "eu-central-1",
                "--no-cli-pager",
                "--output",
                "json",
                "sts",
                "get-caller-identity",
            ],
        )

    def test_invoke_checks_function_error_even_with_http_200_and_saves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            metadata = {"StatusCode": 200, "FunctionError": "Unhandled"}
            with patch.object(task2, "aws", return_value=metadata):
                with self.assertRaisesRegex(ValueError, "invocation failed"):
                    task2.invoke(OUT, folder)
            self.assertEqual(json.loads((folder / "invoke.json").read_text()), metadata)

    def test_invoke_requires_exact_message_and_message_id(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch.object(task2, "aws", return_value={"StatusCode": 200}) as aws:
                for payload in (
                    {},
                    {"message": "Hello from Lambda!", "message_id": "id"},
                    {"message": "Hello, world!"},
                    [],
                ):
                    with self.subTest(payload=payload):
                        (folder / "response.json").write_text(json.dumps(payload))
                        with self.assertRaisesRegex(ValueError, "Unexpected Lambda result"):
                            task2.invoke(OUT, folder)
                (folder / "response.json").write_text(
                    json.dumps({"message": "Hello, world!", "message_id": "id"})
                )
                with patch("builtins.print"):
                    task2.invoke(OUT, folder)
                args = aws.call_args.args
                self.assertIn(OUT["function_arn"], args)
                self.assertIn("RequestResponse", args)
                self.assertEqual(args[-1], str(folder / "response.json"))

    def test_demo_uses_existing_role_group_and_function_with_auto_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(task2, "datetime") as clock,
                patch.object(task2, "aws", return_value={}) as aws,
                patch("builtins.print"),
            ):
                clock.now.return_value = datetime(2026, 10, 1, 22, 59, tzinfo=timezone.utc)
                task2.demo_create(OUT, Path(directory), 180)
                args = aws.call_args.args
                self.assertEqual(args[1:4], ("scheduler", "create-schedule", "--cli-input-json"))
                request = json.loads(args[-1])
                self.assertEqual(request["Name"], "get-task2-demo")
                self.assertNotEqual(request["Name"], OUT["schedule_name"])
                self.assertEqual(request["GroupName"], OUT["schedule_group"])
                self.assertEqual(request["Target"]["Arn"], OUT["function_arn"])
                self.assertEqual(request["Target"]["RoleArn"], OUT["scheduler_role_arn"])
                self.assertEqual(request["ScheduleExpression"], "at(2026-10-01T23:02:00)")
                self.assertEqual(request["ScheduleExpressionTimezone"], "UTC")
                self.assertEqual(request["ActionAfterCompletion"], "DELETE")
                self.assertEqual(request["FlexibleTimeWindow"], {"Mode": "OFF"})
                self.assertEqual(
                    json.loads((Path(directory) / "request.json").read_text()), request
                )

    def test_invalid_demo_delay_does_not_call_aws(self):
        with patch.object(task2, "aws") as aws:
            for delay in (0, 59, 3601):
                with self.assertRaisesRegex(ValueError, "DELAY"):
                    task2.demo_create(OUT, Path("unused"), delay)
            aws.assert_not_called()

    def test_demo_deletion_is_scoped_and_only_missing_resource_is_ignored(self):
        with patch.object(task2, "aws", return_value={}) as aws:
            task2.demo_operation(OUT, "delete-schedule")
            aws.assert_called_once_with(
                OUT,
                "scheduler",
                "delete-schedule",
                "--name",
                "get-task2-demo",
                "--group-name",
                "get-task2",
            )
        for code, ignored in (
            ("ResourceNotFoundException", True),
            ("AccessDeniedException", False),
            ("ExpiredTokenException", False),
        ):
            error = subprocess.CalledProcessError(
                254, ["aws"], stderr="An error occurred (" + code + ")"
            )
            with self.subTest(code=code), patch.object(task2, "aws", side_effect=error):
                if ignored:
                    self.assertEqual(
                        task2.demo_operation(OUT, "delete-schedule")["Status"], "ABSENT"
                    )
                else:
                    with self.assertRaises(subprocess.CalledProcessError):
                        task2.demo_operation(OUT, "delete-schedule")


if __name__ == "__main__":
    unittest.main()
