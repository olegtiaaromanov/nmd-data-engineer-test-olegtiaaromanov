## Update the following terraform code to meet the project requirements
## We have provided some sample code to help you get started

resource "aws_s3_bucket" "input_s3" {
  bucket = "${local.app_name}-input-bucket"
  tags = merge({
        Name        = "${local.app_name}-input-bucket"
        Environment = "${var.env}"
    }, local.default_tags
  )
  force_destroy = true
}

module "lambda_function" {
  source                  = "../modules/lambda"
  lambda_name             = "${local.app_name}-file-processor"
  role_name               = "${local.app_name}-file-processor-role"
  log_retention_in_days   = 14
  image_uri               = "${module.ecr_repo.repository_url}:latest"
  timeout                 = 15
  memory_size             = 256
  environment_variables   = {
    EXAMPLE_VAR = "value"
  }

  default_tags = local.default_tags
}

module "ecr_repo" {
  source    = "../modules/ecr-repo"
  repo_name = "${local.app_name}-ecr"
  default_tags = local.default_tags
}

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_s3.id
}

resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = aws_s3_bucket.input_s3.id
  lambda_function {
    lambda_function_arn = module.lambda_function.lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "*"
    filter_suffix       = ".csv"
  }
}
