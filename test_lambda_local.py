
import importlib.util
import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make application modules importable
sys.path.insert(0, str(Path("app").resolve()))

# Import lambda.py without conflicting with Python's lambda keyword
spec = importlib.util.spec_from_file_location(
    "orders_lambda", "app/lambda.py"
)
orders_lambda = importlib.util.module_from_spec(spec)

# Prevent boto3 from contacting AWS during module import
import boto3
original_client = boto3.client
boto3.client = MagicMock()

try:
    spec.loader.exec_module(orders_lambda)
finally:
    boto3.client = original_client

# Simulate S3 input
sample_data = Path("sample_orders.csv").read_bytes()

mock_s3 = MagicMock()
mock_s3.get_object.return_value = {
    "Body": io.BytesIO(sample_data)
}

orders_lambda.s3 = mock_s3

# Simulate Lambda environment variable
os.environ["OUTPUT_BUCKET"] = "test-output-bucket"

# Simulate an S3 ObjectCreated event
event = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "test-input-bucket"},
                "object": {"key": "sample_orders.csv"}
            }
        }
    ]
}

result = orders_lambda.lambda_handler(event, None)

print("Lambda result:")
print(result)

print("\nGenerated reports:")
for call in mock_s3.put_object.call_args_list:
    kwargs = call.kwargs
    print("\nFile:", kwargs["Key"])
    print(kwargs["Body"].decode("utf-8"))

assert result["statusCode"] == 200
assert mock_s3.put_object.call_count == 3
print("\nSUCCESS: All three CSV reports generated.")

