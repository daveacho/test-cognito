# test-cognito
testing cognito backup and restore
repository-root/
├── cognito_backup/
│   ├── lambda_functions.py  # Provided script
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_lambda_function.py  # New test file


repository-root/
├── cognito_backup_restore/
│   ├── lambda_code/
│   │   ├── config.py
│   │   ├── aws_clients.py
│   │   ├── backup.py
│   │   ├── dynamodb_update.py
│   │   ├── restore.py
│   │   ├── lambda_handler.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_lambda_function.py


repository-root/
├── cognito_backup_restore/
│   ├── lambda_code/
│   │   ├── config.py
│   │   ├── aws_clients.py
│   │   ├── backup.py
│   │   ├── dynamodb_update.py
│   │   ├── restore.py
│   │   ├── lambda_handler.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_lambda_function.py
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── lambda/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   ├── ecr/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   ├── s3/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   ├── dynamodb/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   ├── iam/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
├── .github/
│   ├── workflows/
│   │   ├── pr-check.yml
│   │   ├── pr-check-terraform.yml
│   │   ├── deploy-lambda.yml
│   │   ├── deploy-terraform.yml