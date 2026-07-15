data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name           = "${var.project_name}-${var.environment}"
  deploy_compute = var.enable_database && var.deploy_compute
  account_id     = data.aws_caller_identity.current.account_id
}

resource "aws_ecr_repository" "reviewer" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "reviewer" {
  repository = aws_ecr_repository.reviewer.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain the 20 newest images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_s3_bucket" "documents" {
  bucket = "${local.name}-documents-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    id     = "short-retention"
    status = "Enabled"
    filter {}
    expiration {
      days = var.document_retention_days
    }
  }
}

resource "aws_sqs_queue" "dead_letter" {
  name                        = "${local.name}-reviews-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  message_retention_seconds   = 1209600
}

resource "aws_sqs_queue" "reviews" {
  name                        = "${local.name}-reviews.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 5400
  message_retention_seconds   = 345600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
}

resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name}-frontend-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = local.name
  description                       = "Private S3 access for Reviewer frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "frontend-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    target_origin_id       = "frontend-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "frontend_bucket" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_bucket.json
}

resource "aws_vpc" "database" {
  count                = var.enable_database ? 1 : 0
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "database" {
  count                   = var.enable_database ? 2 : 0
  vpc_id                  = aws_vpc.database[0].id
  cidr_block              = cidrsubnet(aws_vpc.database[0].cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
}

resource "aws_db_subnet_group" "database" {
  count      = var.enable_database ? 1 : 0
  name       = local.name
  subnet_ids = aws_subnet.database[*].id
}

resource "aws_security_group" "database" {
  count       = var.enable_database ? 1 : 0
  name        = "${local.name}-database"
  description = "Aurora is accessed only through the RDS Data API"
  vpc_id      = aws_vpc.database[0].id
}

resource "aws_rds_cluster" "reviewer" {
  count                       = var.enable_database ? 1 : 0
  cluster_identifier          = local.name
  engine                      = "aurora-postgresql"
  engine_mode                 = "provisioned"
  engine_version              = var.aurora_engine_version
  database_name               = var.database_name
  master_username             = "reviewer_admin"
  manage_master_user_password = true
  enable_http_endpoint        = true
  storage_encrypted           = true
  db_subnet_group_name        = aws_db_subnet_group.database[0].name
  vpc_security_group_ids      = [aws_security_group.database[0].id]
  deletion_protection         = var.protect_database
  skip_final_snapshot         = !var.protect_database
  final_snapshot_identifier   = var.protect_database ? "${local.name}-final" : null

  serverlessv2_scaling_configuration {
    min_capacity             = 0
    max_capacity             = 4
    seconds_until_auto_pause = 600
  }
}

resource "aws_rds_cluster_instance" "reviewer" {
  count              = var.enable_database ? 1 : 0
  identifier         = "${local.name}-writer"
  cluster_identifier = aws_rds_cluster.reviewer[0].id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.reviewer[0].engine
  engine_version     = aws_rds_cluster.reviewer[0].engine_version
}

resource "aws_iam_role" "lambda" {
  count = local.deploy_compute ? 1 : 0
  name  = "${local.name}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  count      = local.deploy_compute ? 1 : 0
  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda" {
  count = local.deploy_compute ? 1 : 0
  name  = "${local.name}-runtime"
  role  = aws_iam_role.lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = ["${aws_s3_bucket.documents.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ChangeMessageVisibility",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ReceiveMessage",
          "sqs:SendMessage"
        ]
        Resource = [aws_sqs_queue.reviews.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["rds-data:ExecuteStatement"]
        Resource = [aws_rds_cluster.reviewer[0].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_rds_cluster.reviewer[0].master_user_secret[0].secret_arn]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  count             = local.deploy_compute ? 1 : 0
  name              = "/aws/lambda/${local.name}-api"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "worker" {
  count             = local.deploy_compute ? 1 : 0
  name              = "/aws/lambda/${local.name}-worker"
  retention_in_days = 14
}

resource "aws_lambda_function" "api" {
  count         = local.deploy_compute ? 1 : 0
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda[0].arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["arm64"]
  memory_size   = 1536
  timeout       = 30

  image_config {
    command = ["reviewer.lambda_api.handler"]
  }

  environment {
    variables = {
      APP_ENV           = var.environment
      CORS_ORIGINS       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
      DOCUMENT_BUCKET    = aws_s3_bucket.documents.id
      JOB_BACKEND        = "sqs"
      MAX_UPLOAD_BYTES   = tostring(var.max_upload_bytes)
      RDS_CLUSTER_ARN    = aws_rds_cluster.reviewer[0].arn
      RDS_DATABASE       = var.database_name
      RDS_SECRET_ARN     = aws_rds_cluster.reviewer[0].master_user_secret[0].secret_arn
      REPOSITORY_BACKEND = "rds-data"
      REVIEW_QUEUE_URL   = aws_sqs_queue.reviews.url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy.lambda,
    aws_iam_role_policy_attachment.lambda_logs,
  ]
}

resource "aws_lambda_function" "worker" {
  count         = local.deploy_compute ? 1 : 0
  function_name = "${local.name}-worker"
  role          = aws_iam_role.lambda[0].arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["arm64"]
  memory_size   = 4096
  timeout       = 900

  image_config {
    command = ["reviewer.lambda_worker.handler"]
  }

  environment {
    variables = {
      APP_ENV           = var.environment
      DOCUMENT_BUCKET    = aws_s3_bucket.documents.id
      JOB_BACKEND        = "sqs"
      RDS_CLUSTER_ARN    = aws_rds_cluster.reviewer[0].arn
      RDS_DATABASE       = var.database_name
      RDS_SECRET_ARN     = aws_rds_cluster.reviewer[0].master_user_secret[0].secret_arn
      REPOSITORY_BACKEND = "rds-data"
      REVIEW_QUEUE_URL   = aws_sqs_queue.reviews.url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.worker,
    aws_iam_role_policy.lambda,
    aws_iam_role_policy_attachment.lambda_logs,
  ]
}

resource "aws_lambda_event_source_mapping" "reviews" {
  count                              = local.deploy_compute ? 1 : 0
  event_source_arn                   = aws_sqs_queue.reviews.arn
  function_name                      = aws_lambda_function.worker[0].arn
  batch_size                         = 1
  function_response_types            = ["ReportBatchItemFailures"]
  maximum_batching_window_in_seconds = 1
}

resource "aws_apigatewayv2_api" "reviewer" {
  count         = local.deploy_compute ? 1 : 0
  name          = local.name
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://${aws_cloudfront_distribution.frontend.domain_name}"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  count                  = local.deploy_compute ? 1 : 0
  api_id                 = aws_apigatewayv2_api.reviewer[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  count     = local.deploy_compute ? 1 : 0
  api_id    = aws_apigatewayv2_api.reviewer[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda[0].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  count       = local.deploy_compute ? 1 : 0
  api_id      = aws_apigatewayv2_api.reviewer[0].id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  count         = local.deploy_compute ? 1 : 0
  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.reviewer[0].execution_arn}/*/*"
}
