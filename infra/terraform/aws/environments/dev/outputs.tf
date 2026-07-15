output "ecr_repository_url" {
  value = aws_ecr_repository.reviewer.repository_url
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}

output "api_url" {
  value = local.deploy_compute ? aws_apigatewayv2_api.reviewer[0].api_endpoint : null
}

output "document_bucket" {
  value = aws_s3_bucket.documents.id
}

output "review_queue_url" {
  value = aws_sqs_queue.reviews.url
}

output "database_cluster_arn" {
  value = var.enable_database ? aws_rds_cluster.reviewer[0].arn : null
}

