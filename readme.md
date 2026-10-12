## New Math Data — AWS Orders Analytics Assessment

This project implements an event-driven AWS data-processing pipeline using Amazon S3, AWS Lambda, Amazon ECR, Docker, Python, and Terraform.

See the original [Assessment Instructions](instructions.md).

## Architecture

```text
CSV Upload
    |
    v
Amazon S3 (Input Bucket)
    |
    | S3 ObjectCreated event (.csv files)
    v
AWS Lambda (ARM64 Docker Container)
    |
    | Read CSV using pandas
    | Calculate order profitability
    | Aggregate shipping and order data
    v
Amazon S3 (Output Bucket)
    |
    +-- most_profitable_region.csv
    +-- most_common_ship_method.csv
    +-- orders_by_category.csv
```

## Analytics

The Lambda function generates three reports for each uploaded CSV:

1. **Most profitable region:** Calculates order-line profit using list price, discount percentage, cost price, and quantity, then identifies the region with the highest total profit.
2. **Most common shipping method by category:** Counts shipping-method occurrences for each product category and selects the most frequent method. Alphabetical ordering provides deterministic tie-breaking.
3. **Orders by category and sub-category:** Counts distinct order IDs within each category/sub-category combination.

## Technology Stack

- Python 3.12
- pandas and boto3
- AWS Lambda with ARM64 container image
- Amazon S3 for input and output storage
- Amazon ECR for container images
- Terraform for infrastructure provisioning
- Amazon CloudWatch for Lambda logs

## Deployment

### Prerequisites

- AWS CLI with valid assessment credentials
- Terraform
- Docker with Buildx support
- AWS IAM permissions for the required services

Configure an AWS CLI profile and verify access:

```bash
aws sts get-caller-identity --profile nmd-assessment
```

### Terraform configuration

Set the appropriate values in `terraform/assignment/vars.tfvars`, including:

```hcl
aws_profile    = "nmd-assessment"
region_name    = "us-west-2"
candidate_name = "olegtiaaromanov"
```

Keep the project and environment values defined for the assessment.

The S3 Terraform backend uses the assessment account's state bucket. Initialize Terraform using a unique state key:

```bash
cd terraform/assignment

export AWS_PROFILE=nmd-assessment
export AWS_REGION=us-west-2

terraform init -reconfigure \
  -backend-config="key=nmd-assignment-olegtiaaromanov.tfstate"
```

### Create the ECR repository

The ECR repository must exist before the Lambda container image can be pushed.

```bash
terraform apply \
  -var-file="vars.tfvars" \
  -target=module.ecr_repo
```

This targeted apply is used only for initial ECR bootstrapping.

### Build and push the container

From the repository root:

```bash
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --load \
  -t nmd-orders-lambda:latest .
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password \
  --region us-west-2 \
  --profile nmd-assessment \
  | docker login --username AWS --password-stdin \
    888577066340.dkr.ecr.us-west-2.amazonaws.com
```

Tag and push the image:

```bash
docker tag nmd-orders-lambda:latest \
  888577066340.dkr.ecr.us-west-2.amazonaws.com/nmd-assignment-olegtiaaromanov-ecr:latest

docker push \
  888577066340.dkr.ecr.us-west-2.amazonaws.com/nmd-assignment-olegtiaaromanov-ecr:latest
```

### Deploy the remaining infrastructure

```bash
cd terraform/assignment

terraform validate
terraform plan -var-file="vars.tfvars"
terraform apply -var-file="vars.tfvars"
```

The infrastructure provisions input and output S3 buckets, the container-based Lambda function, IAM permissions, and an S3 event notification.

## Testing

### Local test

Install the Python dependencies:

```bash
pip install -r app/requirements.txt
```

Run the local Lambda test, which mocks S3 interactions:

```bash
python test_lambda_local.py
```

### End-to-end AWS test

Upload the sample CSV from the repository root:

```bash
aws s3 cp sample_orders.csv \
  s3://nmd-assignment-olegtiaaromanov-input-bucket/sample_orders.csv \
  --profile nmd-assessment \
  --region us-west-2
```

Verify the generated reports:

```bash
aws s3 ls \
  s3://nmd-assignment-olegtiaaromanov-output-bucket/ \
  --recursive \
  --profile nmd-assessment \
  --region us-west-2
```

Expected files:

```text
reports/sample_orders/most_profitable_region.csv
reports/sample_orders/most_common_ship_method.csv
reports/sample_orders/orders_by_category.csv
```

### Verified sample results

- Most profitable region: **East**, total profit **$2,465.50**
- Furniture: **Same Day**, 2 shipping records
- Office Supplies: **Standard Class**, 4 shipping records
- Technology: **Same Day**, 2 shipping records
- Category/sub-category report: **11 groups**, totaling **20 distinct-order counts across groups**

The end-to-end AWS test successfully generated all three reports, matching the local test results.

## Output Partitioning Strategy

Output reports are organized by the input object's S3 key without its `.csv` extension:

```text
reports/<input-object-key-without-extension>/<report-name>.csv
```

For example, uploading `sample_orders.csv` generates:

```text
reports/sample_orders/most_profitable_region.csv
reports/sample_orders/most_common_ship_method.csv
reports/sample_orders/orders_by_category.csv
```

This provides logical separation by input file, making reports easier to locate and preventing unrelated source filenames from writing to the same report path.

Reprocessing the same input key overwrites its corresponding reports, making output behavior deterministic for repeated uploads.

For larger-scale analytics, an alternative would be date-based partitioning, such as `year=2026/month=10/day=12/`, depending on downstream query and retention requirements.

## Security

- The Lambda execution role uses the AWS-managed basic execution policy for CloudWatch logging.
- An additional IAM policy grants `s3:GetObject` on the input bucket's objects and `s3:PutObject` on the output bucket's objects.
- Both S3 buckets have public access blocked.
- AWS credentials are provided through the AWS CLI profile rather than embedded in application code.
- Terraform state is stored in an S3 backend.

## Operational Considerations

- The Lambda function has a 60-second timeout and 512 MB of memory.
- CloudWatch log retention is configured for 14 days.
- The current implementation reads each CSV into memory with pandas, which is appropriate for the assessment dataset.
- For significantly larger files, consider chunked processing or AWS Glue.
