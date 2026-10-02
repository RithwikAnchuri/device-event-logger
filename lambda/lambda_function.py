import json
import os
import time

import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
REQUIRED = ("device_id", "event_id", "type")


def resp(status, body):
    """Build the response shape API Gateway's proxy integration requires."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),  # default=str handles DynamoDB Decimals
    }


def lambda_handler(event, context):
    method = event.get("httpMethod")
    if method == "POST":
        return create_event(event)
    if method == "GET":
        return list_events()
    return resp(405, {"error": "method not allowed"})


def create_event(event):
    print("received body:", event.get("body"))

    # 1. Parse
    try:
        data = json.loads(event.get("body") or "")
    except json.JSONDecodeError:
        return resp(400, {"error": "body is not valid JSON"})
    if not isinstance(data, dict):
        return resp(400, {"error": "body must be a JSON object"})

    # 2. Validate
    for field in REQUIRED:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return resp(400, {"error": f"missing or invalid field: {field}"})

    # 3. Store, rejecting duplicates atomically
    item = {f: data[f] for f in REQUIRED}
    item["received_at"] = int(time.time())  # server-side timestamp
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(event_id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return resp(409, {"error": "duplicate event_id"})
        raise  # unexpected errors become a 500 and appear in CloudWatch

    return resp(201, {"status": "stored", "event_id": item["event_id"]})


def list_events():
    result = table.scan(Limit=50)
    items = sorted(result["Items"], key=lambda i: i["received_at"], reverse=True)
    return resp(200, {"events": items})
