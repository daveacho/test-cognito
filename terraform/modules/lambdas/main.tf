# IAM role for Lambda function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.projectName}-${var.environment}-lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.projectName}-${var.environment}-Cognito-Backup-Lambda-Execution-Role"
    
    
  }
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.projectName}-${var.environment}-cognito-lambda-backup-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${var.s3_bucket_arn}",
          "${var.s3_bucket_arn}/*" 
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:DescribeUserPool",
          "cognito-idp:ListUserPoolClients",
          "cognito-idp:DescribeUserPoolClient",
          "cognito-idp:ListUsers",
          "cognito-idp:ListGroups",
          "cognito-idp:CreateUserPool",
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:CreateGroup"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "cognito_backup_restore" {
  function_name    = "${var.projectName}-${var.environment}-cognito-backup-restore"
  role             = aws_iam_role.lambda_execution_role.arn
  package_type     = "Image"
  image_uri        =  var.lambda_image_uri
  timeout          = 600
  memory_size      = 2048                        # very memory intensive process

  environment {
    variables = {
      BACKUP_BUCKET_NAME      = var.s3_bucket_name
    }
  }
  tags = {
    Name = "${var.projectName}-${var.environment}-Cognito-Backup-restore"
  }
}

