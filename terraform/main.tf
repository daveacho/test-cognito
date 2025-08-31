module "ecr" {
  source          = "./modules/ecr"
  projectName     = var.projectName
  environment     = var.environment
  repository_name = var.repository_name
}
module "lambdas" {
  source      = "./modules/lambdas"
  projectName = var.projectName
  environment = var.environment

  s3_bucket_name   = module.s3.s3_bucket_name
  s3_bucket_arn    = module.s3.s3_bucket_arn
  #lambda_image_uri = "{module.ecr.ecr_repository_url}:cognito_backup_restore-latest"
  # lambda_image_uri = "${data.aws_ecr_repository.test_name.repository_url}:cognito_backup_restore-latest"
  lambda_image_uri = data.aws_ecr_image.lambda_image.image_uri
}

module "s3" {
  source                    = "./modules/s3"
  projectName               = var.projectName
  environment               = var.environment
  lambda_execution_role_arn = module.lambdas.lambda_execution_role_arn
  lambda_function_name      = module.lambdas.cognito_backup_lambda_function_name
}


# data "aws_ecr_repository" "test_name" {
#   name = "backups"
# }
####
data "aws_ecr_image" "lambda_image" {
  repository_name = "backups"
  image_tag       = "cognito_backup_restore-latest"
}