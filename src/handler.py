"""Publish the assignment's message to the configured SNS topic."""

import json
import logging
import os

import boto3
from botocore.config import Config

MESSAGE = "Hello, world!"
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
SNS = boto3.client(
    "sns",
    config=Config(
        connect_timeout=2,
        read_timeout=2,
        retries={"mode": "standard", "total_max_attempts": 2},
    ),
)


def lambda_handler(event, context):
    """Let publishing failures propagate so Lambda records a failed invocation."""
    topic_arn = os.environ["SNS_TOPIC_ARN"]
    if not topic_arn.strip():
        raise ValueError("SNS_TOPIC_ARN must not be empty")
    response = SNS.publish(TopicArn=topic_arn, Message=MESSAGE)
    message_id = response["MessageId"]
    LOGGER.info(
        json.dumps(
            {
                "event": "published",
                "request_id": context.aws_request_id,
                "message_id": message_id,
            }
        )
    )
    return {"message_id": message_id, "message": MESSAGE}
