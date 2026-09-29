"""Exercise the SNS API boundary without AWS access or email delivery."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

with patch.dict(
    os.environ,
    {
        "AWS_DEFAULT_REGION": "eu-central-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
    },
):
    from src import handler

TOPIC = "arn:aws:sns:eu-central-1:123456789012:test-notifications"
CONTEXT = SimpleNamespace(aws_request_id="test-request")


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client(
            "sns",
            region_name="eu-central-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        self.stub = Stubber(self.client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        client_patch = patch.object(handler, "SNS", self.client)
        client_patch.start()
        self.addCleanup(client_patch.stop)

    def test_publishes_exact_plaintext_message(self):
        self.stub.add_response(
            "publish", {"MessageId": "message-123"}, {"TopicArn": TOPIC, "Message": "Hello, world!"}
        )
        with (
            patch.dict(os.environ, {"SNS_TOPIC_ARN": TOPIC}),
            self.assertLogs(handler.LOGGER, level="INFO") as logs,
        ):
            result = handler.lambda_handler({}, CONTEXT)
        self.assertEqual(result, {"message_id": "message-123", "message": "Hello, world!"})
        self.assertIn('"message_id": "message-123"', logs.output[0])
        self.stub.assert_no_pending_responses()

    def test_publish_error_is_not_reported_as_success(self):
        self.stub.add_client_error(
            "publish",
            service_error_code="AuthorizationError",
            expected_params={"TopicArn": TOPIC, "Message": "Hello, world!"},
        )
        with patch.dict(os.environ, {"SNS_TOPIC_ARN": TOPIC}), self.assertRaises(ClientError):
            handler.lambda_handler({}, CONTEXT)
        self.stub.assert_no_pending_responses()

    def test_missing_topic_is_rejected_before_publishing(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(KeyError):
            handler.lambda_handler({}, CONTEXT)

    def test_empty_topic_is_rejected_before_publishing(self):
        with patch.dict(os.environ, {"SNS_TOPIC_ARN": " "}), self.assertRaises(ValueError):
            handler.lambda_handler({}, CONTEXT)


if __name__ == "__main__":
    unittest.main()
