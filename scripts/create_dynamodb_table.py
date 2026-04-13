import os
import sys

import boto3
from botocore.exceptions import ClientError


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    table_name = os.getenv(
        "DYNAMODB_TABLE_NAME", "room-cleanliness-predictions-dev"
    )
    dynamodb = boto3.client("dynamodb", region_name=region)

    try:
        dynamodb.describe_table(TableName=table_name)
        print(f"Table already exists: {table_name}")
        return 0
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code != "ResourceNotFoundException":
            raise

    dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "prediction_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "prediction_id", "KeyType": "HASH"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print(f"Created table: {table_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
