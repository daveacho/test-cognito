# AWS Lambda base image
FROM public.ecr.aws/lambda/python:3.12

# Set working directory to Lambda's task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Install dependencies first (optimized for caching)
COPY cognito_backup_restore/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python function code
COPY cognito_backup_restore/cognito_backup_restore.py ./

# Set Lambda handler
CMD ["cognito_backup_restore.lambda_handler"]
