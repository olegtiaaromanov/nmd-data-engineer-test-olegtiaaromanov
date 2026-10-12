
import io
import json
import logging
import os
from pathlib import PurePosixPath
from urllib.parse import unquote_plus

import boto3
import pandas as pd

import orders_analytics

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def get_s3_path_from_event(event: dict) -> str:
    """Extract the S3 URI of the first uploaded object."""
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    return f"s3://{bucket}/{key}"


def write_report(bucket: str, key: str, dataframe: pd.DataFrame):
    """Write a Pandas DataFrame to S3 as CSV."""
    csv_data = dataframe.to_csv(index=False)

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_data.encode("utf-8"),
        ContentType="text/csv",
    )

    logger.info("Wrote report to s3://%s/%s", bucket, key)


def lambda_handler(event, context):
    """Process S3 CSV uploads and generate three analytics reports."""
    output_bucket = os.environ["OUTPUT_BUCKET"]
    processed = []

    for record in event["Records"]:
        input_bucket = record["s3"]["bucket"]["name"]
        input_key = unquote_plus(record["s3"]["object"]["key"])

        if not input_key.lower().endswith(".csv"):
            logger.info("Skipping non-CSV object: %s", input_key)
            continue

        logger.info("Processing s3://%s/%s", input_bucket, input_key)

        response = s3.get_object(
            Bucket=input_bucket,
            Key=input_key,
        )

        orders_df = pd.read_csv(io.BytesIO(response["Body"].read()))

        if orders_df.empty:
            raise ValueError(f"Input file is empty: {input_key}")

        # 1. Calculate profit per order
        orders_df = orders_analytics.calculate_profit_by_order(
            orders_df
        )

        # 2. Find the most profitable region
        region, profit = (
            orders_analytics.calculate_most_profitable_region(
                orders_df
            )
        )

        region_report = pd.DataFrame([{
            "Region": region,
            "Total Profit": round(float(profit), 2),
        }])

        # 3. Find the most common shipping method per category
        shipping_report = (
            orders_analytics.find_most_common_ship_method(
                orders_df
            )
        )

        # 4. Count orders by category and sub-category
        category_report = (
            orders_analytics.find_number_of_order_per_category(
                orders_df
            )
        )

        # Preserve source path and filename as an output prefix.
        source_path = PurePosixPath(input_key)
        report_prefix = (
            f"reports/{source_path.with_suffix('')}/"
        )

        reports = {
            "most_profitable_region.csv": region_report,
            "most_common_ship_method.csv": shipping_report,
            "orders_by_category.csv": category_report,
        }

        for filename, dataframe in reports.items():
            write_report(
                output_bucket,
                report_prefix + filename,
                dataframe,
            )

        processed.append({
            "input": f"s3://{input_bucket}/{input_key}",
            "output_prefix": f"s3://{output_bucket}/{report_prefix}",
        })

    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": processed,
        }),
    }

