#!/usr/bin/env python3
"""Run explicit live lab operations using Terraform outputs and the AWS CLI."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, capture=True):
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=True,
        timeout=60 if capture else None,
    )


def outputs():
    terraform = os.environ.get("TERRAFORM", "terraform")
    raw = json.loads(run([terraform, "-chdir=terraform", "output", "-json"]).stdout)
    values = {name: item["value"] for name, item in raw.items()}
    required = (
        "region",
        "function_arn",
        "topic_arn",
        "log_group",
        "schedule_name",
        "schedule_group",
        "scheduler_role_arn",
    )
    missing = [name for name in required if not values.get(name)]
    if missing:
        raise ValueError(
            "Deploy this project first; missing Terraform outputs: " + ", ".join(missing)
        )
    return values


def aws_command(out, *args):
    return ["aws", "--region", out["region"], "--no-cli-pager", "--output", "json", *args]


def aws(out, *args):
    result = run(aws_command(out, *args))
    return json.loads(result.stdout) if result.stdout.strip() else {}


def check_identity(out):
    account = out["function_arn"].split(":")[4]
    if aws(out, "sts", "get-caller-identity")["Account"] != account:
        raise ValueError("AWS_PROFILE selects a different account than this Terraform deployment.")


def save(folder, name, data):
    (folder / name).write_text(json.dumps(data, indent=2) + "\n")


def evidence(action):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT / "evidence" / (action + "-" + stamp)
    folder.mkdir(parents=True)
    print("Evidence:", folder)
    return folder


def subscriptions(out):
    return aws(out, "sns", "list-subscriptions-by-topic", "--topic-arn", out["topic_arn"])


def status(out, folder):
    result = {
        "lambda": aws(
            out, "lambda", "get-function-configuration", "--function-name", out["function_arn"]
        ),
        "schedule": aws(
            out,
            "scheduler",
            "get-schedule",
            "--name",
            out["schedule_name"],
            "--group-name",
            out["schedule_group"],
        ),
        "subscriptions": subscriptions(out),
    }
    save(folder, "status.json", result)
    confirmed = sum(
        s["SubscriptionArn"].startswith("arn:")
        for s in result["subscriptions"].get("Subscriptions", [])
    )
    print("Lambda state:", result["lambda"]["State"])
    print(
        "Schedule:",
        result["schedule"]["State"],
        result["schedule"]["ScheduleExpression"],
        result["schedule"].get("ScheduleExpressionTimezone", "UTC"),
    )
    print("Confirmed subscriptions:", confirmed)
    if not confirmed:
        print("Add and confirm an Email subscription manually before testing inbox delivery.")


def invoke(out, folder):
    payload_path = folder / "response.json"
    metadata = aws(
        out,
        "lambda",
        "invoke",
        "--function-name",
        out["function_arn"],
        "--invocation-type",
        "RequestResponse",
        "--cli-binary-format",
        "raw-in-base64-out",
        "--payload",
        "{}",
        str(payload_path),
    )
    save(folder, "invoke.json", metadata)
    if metadata.get("StatusCode") != 200 or metadata.get("FunctionError"):
        raise ValueError(
            "Lambda invocation failed; inspect invoke.json and response.json in " + str(folder)
        )
    payload = json.loads(payload_path.read_text())
    if (
        not isinstance(payload, dict)
        or payload.get("message") != "Hello, world!"
        or not payload.get("message_id")
    ):
        raise ValueError("Unexpected Lambda result; inspect " + str(payload_path))
    print("SNS accepted Hello, world! MessageId:", payload["message_id"])
    print("Verify actual receipt in the subscriber's inbox separately.")


def demo_name(out):
    return out["schedule_group"] + "-demo"


def demo_create(out, folder, delay):
    if not 60 <= delay <= 3600:
        raise ValueError("DELAY must be between 60 and 3600 seconds.")
    when = datetime.now(timezone.utc) + timedelta(seconds=delay)
    request = {
        "Name": demo_name(out),
        "GroupName": out["schedule_group"],
        "Description": "Temporary Task 2 email demo; automatically deleted after completion.",
        "ScheduleExpression": "at(" + when.strftime("%Y-%m-%dT%H:%M:%S") + ")",
        "ScheduleExpressionTimezone": "UTC",
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "State": "ENABLED",
        "ActionAfterCompletion": "DELETE",
        "Target": {
            "Arn": out["function_arn"],
            "RoleArn": out["scheduler_role_arn"],
            "Input": json.dumps({"source": "demo-schedule"}),
            "RetryPolicy": {"MaximumEventAgeInSeconds": 300, "MaximumRetryAttempts": 2},
        },
    }
    save(folder, "request.json", request)
    result = aws(out, "scheduler", "create-schedule", "--cli-input-json", json.dumps(request))
    save(folder, "schedule.json", result)
    print("Demo scheduled for", when.strftime("%Y-%m-%d %H:%M:%S UTC"))
    print("Daily schedule unchanged. Check make logs and the recipient's inbox after execution.")


def demo_operation(out, operation):
    try:
        return aws(
            out,
            "scheduler",
            operation,
            "--name",
            demo_name(out),
            "--group-name",
            out["schedule_group"],
        )
    except subprocess.CalledProcessError as error:
        if "(ResourceNotFoundException)" not in (error.stderr or ""):
            raise
        return {"Name": demo_name(out), "Status": "ABSENT"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "status",
            "subscriptions",
            "invoke",
            "logs",
            "demo-create",
            "demo-status",
            "demo-delete",
        ),
    )
    parser.add_argument("--since", default="10m")
    parser.add_argument("--follow", action="store_true")
    parser.add_argument("--delay", type=int, default=180)
    args = parser.parse_args()
    if args.action == "demo-create" and not 60 <= args.delay <= 3600:
        parser.error("--delay must be between 60 and 3600 seconds")
    out = outputs()
    check_identity(out)
    if args.action == "logs" and args.follow:
        run(
            aws_command(out, "logs", "tail", out["log_group"], "--since", args.since, "--follow"),
            capture=False,
        )
        return
    folder = evidence(args.action)
    if args.action == "status":
        status(out, folder)
    elif args.action == "invoke":
        invoke(out, folder)
    elif args.action == "demo-create":
        demo_create(out, folder, args.delay)
    elif args.action == "logs":
        text = run(aws_command(out, "logs", "tail", out["log_group"], "--since", args.since)).stdout
        (folder / "logs.txt").write_text(text)
        print(text, end="")
    else:
        if args.action == "subscriptions":
            result = subscriptions(out)
        else:
            operation = "get-schedule" if args.action == "demo-status" else "delete-schedule"
            result = demo_operation(out, operation)
        save(folder, "result.json", result)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("Error:", error, file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
