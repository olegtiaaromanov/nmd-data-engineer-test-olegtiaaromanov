import sys
import json
import os
import pandas as pd

import orders_analytics

"""
Modify this lambda function to perform the following questions

1. Find the most profitable Region, and its profit
2. What shipping method is most common for each Category
3. Output a glue table containing the number of orders for each Category and Sub Category
"""


def get_s3_path_from_event(event : dict) -> str:
    "Returns the S3 path from the lambda event record"

def lambda_handler(event, context):
    "Lambda function to process S3 events and perform analytics on orders data"

