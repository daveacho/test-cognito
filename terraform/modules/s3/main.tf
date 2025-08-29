# 11. S3 bucket for backups
resource "aws_s3_bucket" "influxdb_backup_bucket" {
  bucket        = "${var.projectName}-${var.environment}-influxdb-backup-bucket-aaa"
  force_destroy = true

  tags = {
    Name = "${var.projectName}-${var.environment}-influxdb-backup-bucket"
  }

}

# Enable Versioning
resource "aws_s3_bucket_versioning" "influxdb_backup_bucket_versioning" {
  bucket = aws_s3_bucket.influxdb_backup_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 13. Encryption: Use KMS for security
resource "aws_s3_bucket_server_side_encryption_configuration" "backups_bucket_encryption" {
  bucket = aws_s3_bucket.influxdb_backup_bucket.bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# # Configure Lifecycle Policy
resource "aws_s3_bucket_lifecycle_configuration" "influxdb_backup_lifecycle" {
  bucket = aws_s3_bucket.influxdb_backup_bucket.id

  rule {
    id     = "FullBackupRetention"
    status = "Enabled"

    filter {
      prefix = "influx-backups/monthly/"
    }
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 120
    }
  }

  rule {
    id     = "DailyBackupRetention"
    status = "Enabled"
    filter {
      prefix = "influx-backups/daily/"
    }
    expiration {
      days = 35
    }
  }
}

# Configure Bucket Policy for Access Control( Restrict access with an IAM policy to allow only the lambda function)
resource "aws_s3_bucket_policy" "influxdb_backup_policy" {
  bucket = aws_s3_bucket.influxdb_backup_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = var.lambda_execution_role_arn
        }
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.influxdb_backup_bucket.arn}",
          "${aws_s3_bucket.influxdb_backup_bucket.arn}/influx-backups/*"
        ]
      },
      {
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          "${aws_s3_bucket.influxdb_backup_bucket.arn}",
          "${aws_s3_bucket.influxdb_backup_bucket.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "influxdb_backup_public_access" {
  bucket                  = aws_s3_bucket.influxdb_backup_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "Cognito Backup Lambda Logs"
    Environment = var.environment
    Project     = "cognito-backup-restore"
  }
}