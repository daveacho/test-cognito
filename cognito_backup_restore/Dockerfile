FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements.txt

# Copy Python function code
COPY *.py ${LAMBDA_TASK_ROOT}/

#Set the CMD to your handler
CMD ["cognito_backup_restore.lambda_handler"]