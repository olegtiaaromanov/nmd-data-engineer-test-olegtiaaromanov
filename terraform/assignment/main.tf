
# ============================================================
# S3 INPUT BUCKET
# Receives incoming order CSV files
# ============================================================

resource "aws_s3_bucket" "input_s3" {
  bucket        = "${local.app_name}-input-bucket"
  force_destroy = true

  tags = merge({
    Name        = "${local.app_name}-input-bucket"
    Environment = var.env
  }, local.default_tags)
}

# ============================================================
# S3 OUTPUT BUCKET
# Stores generated analytics CSV reports
# ============================================================

resource "aws_s3_bucket" "output_s3" {
  bucket        = "${local.app_name}-output-bucket"
  force_destroy = true

  tags = merge({
    Name        = "${local.app_name}-output-bucket"
    Environment = var.env
  }, local.default_tags)
}

# ============================================================
# S3 SECURITY
# Block public access to both buckets
# ============================================================

resource "aws_s3_bucket_public_access_block" "input_s3" {
  bucket = aws_s3_bucket.input_s3.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "output_s3" {
  bucket = aws_s3_bucket.output_s3.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================
# ECR REPOSITORY
# Stores the Docker image used by Lambda
# ============================================================

module "ecr_repo" {
  source       = "../modules/ecr-repo"
  repo_name    = "${local.app_name}-ecr"
  default_tags = local.default_tags
}

# ============================================================
# LAMBDA FUNCTION
# Processes order files and generates analytics reports
# ============================================================

module "lambda_function" {
  source                = "../modules/lambda"
  lambda_name           = "${local.app_name}-file-processor"
  role_name             = "${local.app_name}-file-processor-role"
  log_retention_in_days = 14

  image_uri   = "${module.ecr_repo.repository_url}:latest"
  timeout     = 60
  memory_size = 512

  environment_variables = {
    OUTPUT_BUCKET = aws_s3_bucket.output_s3.bucket
  }

  default_tags = local.default_tags
}

# ============================================================
# LAMBDA IAM POLICY
# Least-privilege access to input and output S3 buckets
# ============================================================

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${local.app_name}-s3-access"
  role = "${local.app_name}-file-processor-role"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "ReadInputOrders"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.input_s3.arn}/*"
      },
      {
        Sid    = "WriteAnalyticsReports"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.output_s3.arn}/*"
      }
    ]
  })

  depends_on = [
    module.lambda_function
  ]
}

# ============================================================
# LAMBDA INVOCATION PERMISSION
# Allow only the input S3 bucket to invoke Lambda
# ============================================================

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_s3.arn
}

# ============================================================
# S3 EVENT NOTIFICATION
# Invoke Lambda whenever a CSV file is uploaded
# ============================================================

resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = aws_s3_bucket.input_s3.id

  lambda_function {
    lambda_function_arn = module.lambda_function.lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [
    aws_lambda_permission.allow_bucket
  ]
}
