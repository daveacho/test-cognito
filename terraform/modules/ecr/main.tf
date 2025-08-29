## ECR Repository
resource "aws_ecr_repository" "lambda_repo" {
#   name                 = "${var.projectName}-${var.environment}-cognito-backup-restore"
  name                 = var.repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.projectName}-${var.environment}-cognito-backup-restore"
  }
}

# resource "aws_ecr_lifecycle_policy" "lambda_repo_policy" {
#   repository = aws_ecr_repository.lambda_repo.name

#   policy = jsonencode({
#     rules = [
#       {
#         rulePriority = 1
#         description  = "Keep last 10 images"
#         selection = {
#           tagStatus     = "tagged"
#           tagPrefixList = ["main", "develop"]
#           countType     = "imageCountMoreThan"
#           countNumber   = 10
#         }
#         action = {
#           type = "expire"
#         }
#       },
#       {
#         rulePriority = 2
#         description  = "Delete untagged images older than 1 day"
#         selection = {
#           tagStatus   = "untagged"
#           countType   = "sinceImagePushed"
#           countUnit   = "days"
#           countNumber = 1
#         }
#         action = {
#           type = "expire"
#         }
#       }
#     ]
#   })
# }
