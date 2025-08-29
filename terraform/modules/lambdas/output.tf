output "cognito_backup_lambda_function_name" {
  value = aws_lambda_function.cognito_backup_restore.function_name
}

output "cognito_backup_lambda_function_arn" {
  value = aws_lambda_function.cognito_backup_restore.arn
}

output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution_role.arn
}