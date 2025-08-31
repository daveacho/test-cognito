# # import pytest
# # import json
# # import boto3
# # from moto import mock_aws
# # from cognito_backup_restore.lambda_code.lambda_handler import lambda_handler
# # #from cognito_backup_restore.cognito_backup_restore import lambda_handler


# # @pytest.fixture
# # def aws_region():
# #     """Fixture to set the AWS region for tests."""
#####   return 'eu-west-2'  # Default region, can be overridden via environment variable


# # @pytest.fixture
# # def lambda_event():
# #     """Fixture for a sample Lambda event."""
# #     return {
# #         "operation": "backup",
# #         "user_pool_id": None  # Will be set in test
# #     }


# # @pytest.fixture
# # def s3_bucket(aws_region):
# #     """Fixture to create a mock S3 bucket."""
# #     with mock_aws():
# #         s3_client = boto3.client('s3', region_name=aws_region)
# #         bucket_name = 'test-backup-bucket'
# #         s3_client.create_bucket(
# #             Bucket=bucket_name,
# #             CreateBucketConfiguration={'LocationConstraint': aws_region}
# #         )
# #         yield bucket_name


# # @mock_aws
# # def test_lambda_handler_backup_success(lambda_event, s3_bucket, monkeypatch, aws_region):
# #     """Test the backup operation with a valid user pool ID."""
# #     # Mock environment variables
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create a mock user pool
# #     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
# #     user_pool = cognito_client.create_user_pool(PoolName='testPool')
# #     user_pool_id = user_pool['UserPool']['Id']
# #     lambda_event['user_pool_id'] = user_pool_id

# #     # Call the Lambda handler
# #     response = lambda_handler(lambda_event, None)

# #     # Verify response
# #     assert response['statusCode'] == 200
# #     response_body = json.loads(response['body'])
# #     assert response_body['status'] == 'success'
# #     assert 'backup_location' in response_body
# #     assert response_body['backup_location'].startswith(f"s3://{s3_bucket}/cognito-backups/")
# #     assert response_body['users_backed_up'] == 0
# #     assert response_body['groups_backed_up'] == 0

# #     # Verify S3 upload
# #     s3_client = boto3.client('s3', region_name=aws_region)
# #     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
# #     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
# #     backup_data = json.loads(s3_response['Body'].read())
# #     assert backup_data['user_pool']['Name'] == 'testPool'
# #     assert backup_data['users'] == []
# #     assert backup_data['groups'] == []


# # @mock_aws
# # def test_lambda_handler_backup_with_users_and_groups(s3_bucket, monkeypatch, aws_region):
# #     """Test the backup operation with users and groups."""
# #     # Mock environment variables
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create a mock user pool with users and groups
# #     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
# #     user_pool = cognito_client.create_user_pool(PoolName='testPoolWithData')
# #     user_pool_id = user_pool['UserPool']['Id']

# #     # Create a group
# #     cognito_client.create_group(
# #         GroupName='TestGroup',
# #         UserPoolId=user_pool_id,
# #         Description='Test group for backup'
# #     )

# #     # Create a user
# #     cognito_client.admin_create_user(
# #         UserPoolId=user_pool_id,
# #         Username='testuser',
# #         UserAttributes=[
# #             {'Name': 'email', 'Value': 'test@example.com'},
# #             {'Name': 'given_name', 'Value': 'Test'},
# #             {'Name': 'family_name', 'Value': 'User'}
# #         ],
# #         MessageAction='SUPPRESS'
# #     )

# #     # Add user to group
# #     cognito_client.admin_add_user_to_group(
# #         UserPoolId=user_pool_id,
# #         Username='testuser',
# #         GroupName='TestGroup'
# #     )

# #     # Call the Lambda handler
# #     event = {
# #         'operation': 'backup',
# #         'user_pool_id': user_pool_id
# #     }
# #     response = lambda_handler(event, None)

# #     # Verify response
# #     assert response['statusCode'] == 200
# #     response_body = json.loads(response['body'])
# #     assert response_body['status'] == 'success'
# #     assert response_body['users_backed_up'] == 1
# #     assert response_body['groups_backed_up'] == 1

# #     # Verify backup data
# #     s3_client = boto3.client('s3', region_name=aws_region)
# #     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
# #     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
# #     backup_data = json.loads(s3_response['Body'].read())

# #     assert len(backup_data['users']) == 1
# #     assert len(backup_data['groups']) == 1
# #     assert backup_data['users'][0]['Username'] == 'testuser'
# #     assert backup_data['users'][0]['Groups'] == ['TestGroup']
# #     assert backup_data['groups'][0]['GroupName'] == 'TestGroup'


# # @mock_aws
# # def test_lambda_handler_restore_success(s3_bucket, monkeypatch, aws_region):
# #     """Test the restore operation with a valid backup key and target user pool."""
# #     # Mock environment variables
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create a mock source user pool and backup data
# #     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
# #     source_pool = cognito_client.create_user_pool(PoolName='sourcePool')
# #     source_pool_id = source_pool['UserPool']['Id']

# #     # Convert datetime fields to strings to avoid JSON serialization issues
# #     source_pool_copy = source_pool['UserPool'].copy()
# #     for key in ['CreationDate', 'LastModifiedDate']:
# #         if key in source_pool_copy:
# #             source_pool_copy[key] = source_pool_copy[key].isoformat()

# #     # Create a backup in S3
# #     backup_data = {
# #         'timestamp': '2025-08-13T12:00:00Z',
# #         'user_pool': source_pool_copy,
# #         'users': [
# #             {
# #                 'Username': 'testuser',
# #                 'Attributes': [{'Name': 'email', 'Value': 'test@example.com'}],
# #                 'Groups': ['TestGroup'],
# #                 'UserStatus': 'CONFIRMED'
# #             }
# #         ],
# #         'groups': [{'GroupName': 'TestGroup'}]
# #     }
# #     backup_key = f"cognito-backups/{source_pool_id}/2025-08-13_12-00-00.json"
# #     s3_client = boto3.client('s3', region_name=aws_region)
# #     s3_client.put_object(
# #         Bucket=s3_bucket,
# #         Key=backup_key,
# #         Body=json.dumps(backup_data)
# #     )

# #     # Create a mock target user pool
# #     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
# #     target_pool_id = target_pool['UserPool']['Id']

# #     # Call the Lambda handler for restore
# #     event = {
# #         'operation': 'restore',
# #         'backup_key': backup_key,
# #         'target_user_pool_id': target_pool_id
# #     }
# #     response = lambda_handler(event, None)

# #     # Verify response
# #     assert response['statusCode'] == 200
# #     response_body = json.loads(response['body'])
# #     assert response_body['status'] == 'success'
# #     assert response_body['user_pool_id'] == target_pool_id
# #     assert response_body['users_restored'] == 1
# #     assert response_body['groups_restored'] == 1
# #     assert response_body['user_group_memberships_restored'] == 1
# #     assert response_body['failed_users'] == []


# # @mock_aws
# # def test_lambda_handler_restore_missing_target_pool_id(s3_bucket, monkeypatch, aws_region):
# #     """Test the restore operation with missing target_user_pool_id."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     event = {
# #         'operation': 'restore',
# #         'backup_key': 'cognito-backups/test-pool/backup.json'
# #     }
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 400
# #     assert json.loads(response['body'])['error'] == 'target_user_pool_id is required for restore operation'


# # @mock_aws
# # def test_lambda_handler_restore_nonexistent_target_pool(s3_bucket, monkeypatch, aws_region):
# #     """Test the restore operation with nonexistent target user pool."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create backup data in S3
# #     backup_data = {
# #         'timestamp': '2025-08-13T12:00:00Z',
# #         'user_pool': {'Name': 'TestPool'},
# #         'users': [],
# #         'groups': []
# #     }
# #     backup_key = "cognito-backups/test-pool/backup.json"
# #     s3_client = boto3.client('s3', region_name=aws_region)
# #     s3_client.put_object(
# #         Bucket=s3_bucket,
# #         Key=backup_key,
# #         Body=json.dumps(backup_data)
# #     )

# #     # Call with nonexistent target pool ID
# #     event = {
# #         'operation': 'restore',
# #         'backup_key': backup_key,
# #         'target_user_pool_id': f'{aws_region}_NONEXISTENT'
# #     }
# #     response = lambda_handler(event, None)

# #     # Should return 500 error due to nonexistent pool
# #     assert response['statusCode'] == 500
# #     assert 'error' in json.loads(response['body'])


# # @mock_aws
# # def test_lambda_handler_invalid_operation():
# #     """Test the handler with an invalid operation."""
# #     event = {'operation': 'invalid'}
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 400
# #     assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'


# # @mock_aws
# # def test_lambda_handler_missing_user_pool_id(s3_bucket, monkeypatch, aws_region):
# #     """Test the backup operation with missing user_pool_id."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)
# #     event = {'operation': 'backup'}
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 400
# #     assert json.loads(response['body'])['error'] == 'user_pool_id is required for backup operation'


# # @mock_aws
# # def test_lambda_handler_missing_backup_key(s3_bucket, monkeypatch, aws_region):
# #     """Test the restore operation with missing backup_key."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)
# #     event = {
# #         'operation': 'restore',
# #         'target_user_pool_id': f'{aws_region}_SOMEPOOL'
# #     }
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 400
# #     assert json.loads(response['body'])['error'] == 'backup_key is required for restore operation'


# # @mock_aws
# # def test_lambda_handler_cognito_error(s3_bucket, monkeypatch, aws_region):
# #     """Test the handler when Cognito raises an error."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)
# #     event = {'operation': 'backup', 'user_pool_id': f'{aws_region}_invalidPool'}

# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 500
# #     assert 'error' in json.loads(response['body'])


# # @mock_aws
# # def test_lambda_handler_s3_error(monkeypatch, aws_region):
# #     """Test the handler when S3 operations fail."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', 'nonexistent-bucket')
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create a mock user pool
# #     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
# #     user_pool = cognito_client.create_user_pool(PoolName='testPool')
# #     user_pool_id = user_pool['UserPool']['Id']

# #     event = {
# #         'operation': 'backup',
# #         'user_pool_id': user_pool_id
# #     }
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 500
# #     assert 'error' in json.loads(response['body'])


# # @mock_aws
# # def test_lambda_handler_restore_nonexistent_backup(s3_bucket, monkeypatch, aws_region):
# #     """Test the restore operation with a nonexistent backup key."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# #     monkeypatch.setenv('AWS_REGION', aws_region)

# #     # Create a target user pool
# #     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
# #     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
# #     target_pool_id = target_pool['UserPool']['Id']

# #     event = {
# #         'operation': 'restore',
# #         'backup_key': 'cognito-backups/nonexistent/backup.json',
# #         'target_user_pool_id': target_pool_id
# #     }
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 500
# #     assert 'error' in json.loads(response['body'])

# # ## import pytest
# # # import json
# # # import boto3
# # # from moto import mock_aws
# # # from cognito_backup_restore.cognito_backup_restore import lambda_handler


# # # @pytest.fixture
# # # def lambda_event():
# # #     """Fixture for a sample Lambda event."""
# # #     return {
# # #         "operation": "backup",
# # #         "user_pool_id": None  # Will be set in test
# # #     }


# # # @pytest.fixture
# # # def s3_bucket():
# # #     """Fixture to create a mock S3 bucket."""
# # #     with mock_aws():
# # #         s3_client = boto3.client('s3', region_name='eu-west-2')
# # #         bucket_name = 'test-backup-bucket'
# # #         s3_client.create_bucket(
# # #             Bucket=bucket_name,
# # #             CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'}
# # #         )
# # #         yield bucket_name


# # # @mock_aws
# # # def test_lambda_handler_backup_success(lambda_event, s3_bucket, monkeypatch):
# # #     """Test the backup operation with a valid user pool ID."""
# # #     # Mock environment variable
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     # Create a mock user pool
# # #     cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
# # #     user_pool = cognito_client.create_user_pool(PoolName='testPool')
# # #     user_pool_id = user_pool['UserPool']['Id']  # Get actual mock ID
# # #     lambda_event['user_pool_id'] = user_pool_id  # Update event with correct ID

# # #     # Call the Lambda handler
# # #     response = lambda_handler(lambda_event, None)

# # #     # Verify response
# # #     assert response['statusCode'] == 200
# # #     response_body = json.loads(response['body'])
# # #     assert response_body['status'] == 'success'
# # #     assert 'backup_location' in response_body
# # #     assert response_body['backup_location'].startswith(f"s3://{s3_bucket}/cognito-backups/")
# # #     assert response_body['users_backed_up'] == 0  # No users in mock
# # #     assert response_body['groups_backed_up'] == 0  # No groups in mock

# # #     # Verify S3 upload
# # #     s3_client = boto3.client('s3', region_name='eu-west-2')
# # #     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
# # #     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
# # #     backup_data = json.loads(s3_response['Body'].read())
# # #     assert backup_data['user_pool']['Name'] == 'testPool'
# # #     assert backup_data['users'] == []
# # #     assert backup_data['groups'] == []


# # # @mock_aws
# # # def test_lambda_handler_backup_with_users_and_groups(s3_bucket, monkeypatch):
# # #     """Test the backup operation with users and groups."""
# # #     # Mock environment variable
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     # Create a mock user pool with users and groups
# # #     cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
# # #     user_pool = cognito_client.create_user_pool(PoolName='testPoolWithData')
# # #     user_pool_id = user_pool['UserPool']['Id']

# # #     # Create a group
# # #     cognito_client.create_group(
# # #         GroupName='TestGroup',
# # #         UserPoolId=user_pool_id,
# # #         Description='Test group for backup'
# # #     )

# # #     # Create a user
# # #     cognito_client.admin_create_user(
# # #         UserPoolId=user_pool_id,
# # #         Username='testuser',
# # #         UserAttributes=[
# # #             {'Name': 'email', 'Value': 'test@example.com'},
# # #             {'Name': 'given_name', 'Value': 'Test'},
# # #             {'Name': 'family_name', 'Value': 'User'}
# # #         ],
# # #         MessageAction='SUPPRESS'
# # #     )

# # #     # Add user to group
# # #     cognito_client.admin_add_user_to_group(
# # #         UserPoolId=user_pool_id,
# # #         Username='testuser',
# # #         GroupName='TestGroup'
# # #     )

# # #     # Call the Lambda handler
# # #     event = {
# # #         'operation': 'backup',
# # #         'user_pool_id': user_pool_id
# # #     }
# # #     response = lambda_handler(event, None)

# # #     # Verify response
# # #     assert response['statusCode'] == 200
# # #     response_body = json.loads(response['body'])
# # #     assert response_body['status'] == 'success'
# # #     assert response_body['users_backed_up'] == 1
# # #     assert response_body['groups_backed_up'] == 1

# # #     # Verify backup data
# # #     s3_client = boto3.client('s3', region_name='eu-west-2')
# # #     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
# # #     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
# # #     backup_data = json.loads(s3_response['Body'].read())

# # #     assert len(backup_data['users']) == 1
# # #     assert len(backup_data['groups']) == 1
# # #     assert backup_data['users'][0]['Username'] == 'testuser'
# # #     assert backup_data['users'][0]['Groups'] == ['TestGroup']
# # #     assert backup_data['groups'][0]['GroupName'] == 'TestGroup'


# # # @mock_aws
# # # def test_lambda_handler_restore_success(s3_bucket, monkeypatch):
# # #     """Test the restore operation with a valid backup key and target user pool."""
# # #     # Mock environment variable
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     # Create a mock source user pool and backup data
# # #     cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
# # #     source_pool = cognito_client.create_user_pool(PoolName='sourcePool')
# # #     source_pool_id = source_pool['UserPool']['Id']

# # #     # Convert datetime fields to strings to avoid JSON serialization issues
# # #     source_pool_copy = source_pool['UserPool'].copy()
# # #     for key in ['CreationDate', 'LastModifiedDate']:
# # #         if key in source_pool_copy:
# # #             source_pool_copy[key] = source_pool_copy[key].isoformat()

# # #     # Create a backup in S3
# # #     backup_data = {
# # #         'timestamp': '2025-08-13T12:00:00Z',
# # #         'user_pool': source_pool_copy,
# # #         'users': [
# # #             {
# # #                 'Username': 'testuser',
# # #                 'Attributes': [{'Name': 'email', 'Value': 'test@example.com'}],
# # #                 'Groups': ['TestGroup'],
# # #                 'UserStatus': 'CONFIRMED'
# # #             }
# # #         ],
# # #         'groups': [{'GroupName': 'TestGroup'}]
# # #     }
# # #     backup_key = f"cognito-backups/{source_pool_id}/2025-08-13_12-00-00.json"
# # #     s3_client = boto3.client('s3', region_name='eu-west-2')
# # #     s3_client.put_object(
# # #         Bucket=s3_bucket,
# # #         Key=backup_key,
# # #         Body=json.dumps(backup_data)
# # #     )

# # #     # Create a mock target user pool
# # #     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
# # #     target_pool_id = target_pool['UserPool']['Id']  # Get actual mock ID

# # #     # Call the Lambda handler for restore
# # #     event = {
# # #         'operation': 'restore',
# # #         'backup_key': backup_key,
# # #         'target_user_pool_id': target_pool_id  # Required parameter
# # #     }
# # #     response = lambda_handler(event, None)

# # #     # Verify response
# # #     assert response['statusCode'] == 200
# # #     response_body = json.loads(response['body'])
# # #     assert response_body['status'] == 'success'
# # #     assert response_body['user_pool_id'] == target_pool_id
# # #     assert response_body['users_restored'] == 1
# # #     assert response_body['groups_restored'] == 1
# # #     assert response_body['user_group_memberships_restored'] == 1
# # #     assert response_body['failed_users'] == []


# # # @mock_aws
# # # def test_lambda_handler_restore_missing_target_pool_id(s3_bucket, monkeypatch):
# # #     """Test the restore operation with missing target_user_pool_id."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     event = {
# # #         'operation': 'restore',
# # #         'backup_key': 'cognito-backups/test-pool/backup.json'
# # #         # Missing target_user_pool_id
# # #     }
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 400
# # #     assert json.loads(response['body'])['error'] == 'target_user_pool_id is required for restore operation'


# # # @mock_aws
# # # def test_lambda_handler_restore_nonexistent_target_pool(s3_bucket, monkeypatch):
# # #     """Test the restore operation with nonexistent target user pool."""
# # #     # Mock environment variable
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     # Create backup data in S3
# # #     backup_data = {
# # #         'timestamp': '2025-08-13T12:00:00Z',
# # #         'user_pool': {'Name': 'TestPool'},
# # #         'users': [],
# # #         'groups': []
# # #     }
# # #     backup_key = "cognito-backups/test-pool/backup.json"
# # #     s3_client = boto3.client('s3', region_name='eu-west-2')
# # #     s3_client.put_object(
# # #         Bucket=s3_bucket,
# # #         Key=backup_key,
# # #         Body=json.dumps(backup_data)
# # #     )

# # #     # Call with nonexistent target pool ID
# # #     event = {
# # #         'operation': 'restore',
# # #         'backup_key': backup_key,
# # #         'target_user_pool_id': 'eu-west-2_NONEXISTENT'
# # #     }
# # #     response = lambda_handler(event, None)

# # #     # Should return 500 error due to nonexistent pool
# # #     assert response['statusCode'] == 500
# # #     assert 'error' in json.loads(response['body'])


# # # @mock_aws
# # # def test_lambda_handler_invalid_operation():
# # #     """Test the handler with an invalid operation."""
# # #     event = {'operation': 'invalid'}
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 400
# # #     assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'


# # # @mock_aws
# # # def test_lambda_handler_missing_user_pool_id(s3_bucket, monkeypatch):
# # #     """Test the backup operation with missing user_pool_id."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# # #     event = {'operation': 'backup'}
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 400
# # #     assert json.loads(response['body'])['error'] == 'user_pool_id is required for backup operation'


# # # @mock_aws
# # # def test_lambda_handler_missing_backup_key(s3_bucket, monkeypatch):
# # #     """Test the restore operation with missing backup_key."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# # #     event = {
# # #         'operation': 'restore',
# # #         'target_user_pool_id': 'eu-west-2_SOMEPOOL'
# # #     }
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 400
# # #     assert json.loads(response['body'])['error'] == 'backup_key is required for restore operation'


# # # @mock_aws
# # # def test_lambda_handler_cognito_error(s3_bucket, monkeypatch):
# # #     """Test the handler when Cognito raises an error."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
# # #     event = {'operation': 'backup', 'user_pool_id': 'eu-west-2_invalidPool'}

# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 500
# # #     assert 'error' in json.loads(response['body'])


# # # @mock_aws
# # # def test_lambda_handler_s3_error(monkeypatch):
# # #     """Test the handler when S3 operations fail."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', 'nonexistent-bucket')

# # #     # Create a mock user pool
# # #     cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
# # #     user_pool = cognito_client.create_user_pool(PoolName='testPool')
# # #     user_pool_id = user_pool['UserPool']['Id']

# # #     event = {
# # #         'operation': 'backup',
# # #         'user_pool_id': user_pool_id
# # #     }
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 500
# # #     assert 'error' in json.loads(response['body'])


# # # @mock_aws
# # # def test_lambda_handler_restore_nonexistent_backup(s3_bucket, monkeypatch):
# # #     """Test the restore operation with a nonexistent backup key."""
# # #     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

# # #     # Create a target user pool
# # #     cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
# # #     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
# # #     target_pool_id = target_pool['UserPool']['Id']

# # #     event = {
# # #         'operation': 'restore',
# # #         'backup_key': 'cognito-backups/nonexistent/backup.json',
# # #         'target_user_pool_id': target_pool_id
# # #     }
# # #     response = lambda_handler(event, None)

# # #     assert response['statusCode'] == 500
# # #     assert 'error' in json.loads(response['body'])

# import pytest
# import json
# import boto3
# from moto import mock_aws
# from cognito_backup_restore.lambda_code.lambda_handler import lambda_handler
# from cognito_backup_restore.lambda_code.config import Config
# from cognito_backup_restore.lambda_code.aws_clients import AWSClients
# from cognito_backup_restore.lambda_code.backup import CognitoBackup
# from cognito_backup_restore.lambda_code.restore import CognitoRestore
# from cognito_backup_restore.lambda_code.dynamodb_update import DynamoDBUpdate
# from datetime import datetime, UTC

# @pytest.fixture
# def aws_region():
#     """Fixture to set the AWS region for tests."""
#     return 'eu-west-2'

# @pytest.fixture
# def s3_bucket(aws_region):
#     """Fixture to create a mock S3 bucket."""
#     with mock_aws():
#         s3_client = boto3.client('s3', region_name=aws_region)
#         bucket_name = 'test-backup-bucket'
#         s3_client.create_bucket(
#             Bucket=bucket_name,
#             CreateBucketConfiguration={'LocationConstraint': aws_region}
#         )
#         yield bucket_name

# @pytest.fixture
# def dynamodb_table(aws_region):
#     """Fixture to create a mock DynamoDB table."""
#     with mock_aws():
#         dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
#         table_name = 'test-table'
#         dynamodb_client.create_table(
#             TableName=table_name,
#             KeySchema=[
#                 {'AttributeName': 'PK', 'KeyType': 'HASH'},
#                 {'AttributeName': 'SK', 'KeyType': 'RANGE'}
#             ],
#             AttributeDefinitions=[
#                 {'AttributeName': 'PK', 'AttributeType': 'S'},
#                 {'AttributeName': 'SK', 'AttributeType': 'S'}
#             ],
#             BillingMode='PAY_PER_REQUEST'
#         )
#         yield table_name

# @pytest.fixture
# def aws_clients(s3_bucket, dynamodb_table, aws_region, monkeypatch):
#     """Fixture to create mock AWS clients with environment variables."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('DYNAMODB_TABLE_NAME', dynamodb_table)
#     monkeypatch.setenv('REGION', aws_region)
#     config = Config()
#     return AWSClients(config)

# @pytest.fixture
# def user_pool(aws_region):
#     """Fixture to create a mock Cognito user pool."""
#     with mock_aws():
#         cognito_client = boto3.client('cognito-idp', region_name=aws_region)
#         user_pool = cognito_client.create_user_pool(PoolName='testPool')
#         yield user_pool['UserPool']['Id']

# # Lambda Handler Tests
# @mock_aws
# def test_lambda_handler_backup_success(user_pool, s3_bucket, monkeypatch, aws_region):
#     """Test the backup operation with a valid user pool ID."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     event = {
#         "operation": "backup",
#         "user_pool_id": user_pool
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 200
#     response_body = json.loads(response['body'])
#     assert response_body['status'] == 'success'
#     assert 'backup_location' in response_body
#     assert response_body['backup_location'].startswith(f"s3://{s3_bucket}/cognito-backups/")
#     assert response_body['users_backed_up'] == 0
#     assert response_body['groups_backed_up'] == 0

#     s3_client = boto3.client('s3', region_name=aws_region)
#     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
#     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
#     backup_data = json.loads(s3_response['Body'].read())
#     assert backup_data['user_pool']['Name'] == 'testPool'
#     assert backup_data['users'] == []
#     assert backup_data['groups'] == []

# @mock_aws
# def test_lambda_handler_backup_with_users_and_groups(user_pool, s3_bucket, monkeypatch, aws_region):
#     """Test the backup operation with users and groups."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
#     cognito_client.create_group(
#         GroupName='TestGroup',
#         UserPoolId=user_pool,
#         Description='Test group for backup'
#     )
#     cognito_client.admin_create_user(
#         UserPoolId=user_pool,
#         Username='testuser',
#         UserAttributes=[
#             {'Name': 'email', 'Value': 'test@example.com'},
#             {'Name': 'given_name', 'Value': 'Test'},
#             {'Name': 'family_name', 'Value': 'User'}
#         ],
#         MessageAction='SUPPRESS'
#     )
#     cognito_client.admin_add_user_to_group(
#         UserPoolId=user_pool,
#         Username='testuser',
#         GroupName='TestGroup'
#     )

#     event = {
#         'operation': 'backup',
#         'user_pool_id': user_pool
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 200
#     response_body = json.loads(response['body'])
#     assert response_body['status'] == 'success'
#     assert response_body['users_backed_up'] == 1
#     assert response_body['groups_backed_up'] == 1

#     s3_client = boto3.client('s3', region_name=aws_region)
#     backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
#     s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
#     backup_data = json.loads(s3_response['Body'].read())

#     assert len(backup_data['users']) == 1
#     assert len(backup_data['groups']) == 1
#     assert backup_data['users'][0]['Username'] == 'testuser'
#     assert backup_data['users'][0]['Groups'] == ['TestGroup']
#     assert backup_data['groups'][0]['GroupName'] == 'TestGroup'

# @mock_aws
# def test_lambda_handler_restore_success(user_pool, s3_bucket, dynamodb_table, monkeypatch, aws_region):
#     """Test the restore operation with a valid backup key and target user pool."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('DYNAMODB_TABLE_NAME', dynamodb_table)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     source_pool_id = user_pool
#     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
#     source_pool = cognito_client.describe_user_pool(UserPoolId=source_pool_id)
#     source_pool_copy = source_pool['UserPool'].copy()
#     for key in ['CreationDate', 'LastModifiedDate']:
#         if key in source_pool_copy:
#             source_pool_copy[key] = source_pool_copy[key].isoformat()

#     backup_data = {
#         'timestamp': '2025-08-13T12:00:00Z',
#         'user_pool': source_pool_copy,
#         'users': [
#             {
#                 'Username': 'testuser',
#                 'Attributes': [
#                     {'Name': 'email', 'Value': 'test@example.com'},
#                     {'Name': 'sub', 'Value': 'old-sub-123'}
#                 ],
#                 'Groups': ['TestGroup'],
#                 'UserStatus': 'CONFIRMED'
#             }
#         ],
#         'groups': [{'GroupName': 'TestGroup', 'Description': 'Test group'}]
#     }
#     backup_key = f"cognito-backups/{source_pool_id}/2025-08-13_12-00-00.json"
#     s3_client = boto3.client('s3', region_name=aws_region)
#     s3_client.put_object(
#         Bucket=s3_bucket,
#         Key=backup_key,
#         Body=json.dumps(backup_data)
#     )

#     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
#     target_pool_id = target_pool['UserPool']['Id']

#     dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
#     dynamodb_client.put_item(
#         TableName=dynamodb_table,
#         Item={
#             'PK': {'S': 'u#old-sub-123'},
#             'SK': {'S': 'u#old-sub-123'},
#             'data': {'S': 'test-data'}
#         }
#     )

#     event = {
#         'operation': 'restore',
#         'backup_key': backup_key,
#         'target_user_pool_id': target_pool_id
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 200
#     response_body = json.loads(response['body'])
#     assert response_body['status'] == 'success'
#     assert response_body['user_pool_id'] == target_pool_id
#     assert response_body['users_restored'] == 1
#     assert response_body['groups_restored'] == 1
#     assert response_body['user_group_memberships_restored'] == 1
#     assert response_body['failed_users'] == []
#     assert response_body['dynamodb_records_updated'] == 1
#     assert response_body['dynamodb_failed_updates'] == []

# @mock_aws
# def test_lambda_handler_restore_missing_target_pool_id(s3_bucket, monkeypatch, aws_region):
#     """Test the restore operation with missing target_user_pool_id."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     event = {
#         'operation': 'restore',
#         'backup_key': 'cognito-backups/test-pool/backup.json'
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 400
#     assert json.loads(response['body'])['error'] == 'target_user_pool_id is required for restore operation'

# @mock_aws
# def test_lambda_handler_restore_nonexistent_target_pool(s3_bucket, monkeypatch, aws_region):
#     """Test the restore operation with nonexistent target user pool."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     backup_data = {
#         'timestamp': '2025-08-13T12:00:00Z',
#         'user_pool': {'Name': 'TestPool'},
#         'users': [],
#         'groups': []
#     }
#     backup_key = "cognito-backups/test-pool/backup.json"
#     s3_client = boto3.client('s3', region_name=aws_region)
#     s3_client.put_object(
#         Bucket=s3_bucket,
#         Key=backup_key,
#         Body=json.dumps(backup_data)
#     )

#     event = {
#         'operation': 'restore',
#         'backup_key': backup_key,
#         'target_user_pool_id': f'{aws_region}_NONEXISTENT'
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 500
#     assert 'error' in json.loads(response['body'])

# # @mock_aws
# # def test_lambda_handler_invalid_operation(monkeypatch):
# #     """Test the handler with an invalid operation."""
# #     monkeypatch.setenv('BACKUP_BUCKET_NAME', 'dummy-bucket')  # Set dummy bucket name
# #     event = {'operation': 'invalid'}
# #     response = lambda_handler(event, None)

# #     assert response['statusCode'] == 400
# #     assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'

# @mock_aws
# def test_lambda_handler_invalid_operation(s3_bucket, monkeypatch):
#     """Test the handler with an invalid operation."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
   
#     event = {'operation': 'invalid'}
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 400
#     assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'


# @mock_aws
# def test_lambda_handler_missing_user_pool_id(s3_bucket, monkeypatch, aws_region):
#     """Test the backup operation with missing user_pool_id."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)
#     event = {'operation': 'backup'}
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 400
#     assert json.loads(response['body'])['error'] == 'user_pool_id is required for backup operation'

# @mock_aws
# def test_lambda_handler_missing_backup_key(s3_bucket, monkeypatch, aws_region):
#     """Test the restore operation with missing backup_key."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)
#     event = {
#         'operation': 'restore',
#         'target_user_pool_id': f'{aws_region}_SOMEPOOL'
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 400
#     assert json.loads(response['body'])['error'] == 'backup_key is required for restore operation'

# @mock_aws
# def test_lambda_handler_cognito_error(s3_bucket, monkeypatch, aws_region):
#     """Test the handler when Cognito raises an error."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)
#     event = {'operation': 'backup', 'user_pool_id': f'{aws_region}_invalidPool'}

#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 500
#     assert 'error' in json.loads(response['body'])

# @mock_aws
# def test_lambda_handler_s3_error(monkeypatch, aws_region):
#     """Test the handler when S3 operations fail."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', 'nonexistent-bucket')
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
#     user_pool = cognito_client.create_user_pool(PoolName='testPool')
#     user_pool_id = user_pool['UserPool']['Id']

#     event = {
#         'operation': 'backup',
#         'user_pool_id': user_pool_id
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 500
#     assert 'error' in json.loads(response['body'])

# @mock_aws
# def test_lambda_handler_restore_nonexistent_backup(s3_bucket, monkeypatch, aws_region):
#     """Test the restore operation with a nonexistent backup key."""
#     monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
#     monkeypatch.setenv('AWS_REGION', aws_region)

#     cognito_client = boto3.client('cognito-idp', region_name=aws_region)
#     target_pool = cognito_client.create_user_pool(PoolName='targetPool')
#     target_pool_id = target_pool['UserPool']['Id']

#     event = {
#         'operation': 'restore',
#         'backup_key': 'cognito-backups/nonexistent/backup.json',
#         'target_user_pool_id': target_pool_id
#     }
#     response = lambda_handler(event, None)

#     assert response['statusCode'] == 500
#     assert 'error' in json.loads(response['body'])

# # Unit Tests for Individual Classes
# @mock_aws
# def test_cognito_backup_get_users_with_groups(user_pool, aws_clients):
#     """Test CognitoBackup._get_users_with_groups."""
#     cognito_client = boto3.client('cognito-idp', region_name=aws_clients.cognito_client.meta.region_name)
#     cognito_client.create_group(GroupName='TestGroup', UserPoolId=user_pool)
#     cognito_client.admin_create_user(
#         UserPoolId=user_pool,
#         Username='testuser',
#         UserAttributes=[{'Name': 'email', 'Value': 'test@example.com'}],
#         MessageAction='SUPPRESS'
#     )
#     cognito_client.admin_add_user_to_group(
#         UserPoolId=user_pool,
#         Username='testuser',
#         GroupName='TestGroup'
#     )

#     backup = CognitoBackup(aws_clients)
#     users = backup._get_users_with_groups(user_pool)

#     assert len(users) == 1
#     assert users[0]['Username'] == 'testuser'
#     assert users[0]['Groups'] == ['TestGroup']

# @mock_aws
# def test_cognito_restore_groups(user_pool, aws_clients):
#     """Test CognitoRestore._restore_groups."""
#     groups = [{'GroupName': 'TestGroup', 'Description': 'Test group'}]
#     restore = CognitoRestore(aws_clients)
#     restored_count = restore._restore_groups(groups, user_pool)

#     assert restored_count == 1
#     groups_response = aws_clients.cognito_client.list_groups(UserPoolId=user_pool)
#     assert len(groups_response['Groups']) == 1
#     assert groups_response['Groups'][0]['GroupName'] == 'TestGroup'

# @mock_aws
# def test_dynamodb_update_sub(dynamodb_table, aws_clients):
#     """Test DynamoDBUpdate.update_dynamodb_sub."""
#     dynamodb_client = boto3.client('dynamodb', region_name=aws_clients.dynamodb_client.meta.region_name)
#     dynamodb_client.put_item(
#         TableName=dynamodb_table,
#         Item={
#             'PK': {'S': 'u#old-sub-123'},
#             'SK': {'S': 'u#old-sub-123'},
#             'data': {'S': 'test-data'}
#         }
#     )

#     sub_mappings = [
#         {
#             'username': 'testuser',
#             'old_sub': 'old-sub-123',
#             'new_sub': 'new-sub-456'
#         }
#     ]
#     update = DynamoDBUpdate(aws_clients)
#     result = update.update_dynamodb_sub(sub_mappings)

#     assert result['records_updated'] == 1
#     assert result['failed_updates'] == []
#     assert result['skipped_updates'] == 0

#     response = dynamodb_client.get_item(
#         TableName=dynamodb_table,
#         Key={'PK': {'S': 'u#new-sub-456'}, 'SK': {'S': 'u#new-sub-456'}}
#     )
#     assert 'Item' in response
#     assert response['Item']['data']['S'] == 'test-data'

###################################################################
import pytest
import json
import boto3
from moto import mock_aws
from cognito_backup_restore.lambda_code.lambda_handler import lambda_handler
from cognito_backup_restore.lambda_code.config import Config
from cognito_backup_restore.lambda_code.aws_clients import AWSClients
from cognito_backup_restore.lambda_code.backup import CognitoBackup
from cognito_backup_restore.lambda_code.restore import CognitoRestore
from cognito_backup_restore.lambda_code.dynamodb_update import DynamoDBUpdate



@pytest.fixture
def aws_region():
    """Fixture to set the AWS region for tests."""
    return 'eu-west-2'


@pytest.fixture
def s3_bucket(aws_region):
    """Fixture to create a mock S3 bucket."""
    with mock_aws():
        s3_client = boto3.client('s3', region_name=aws_region)
        bucket_name = 'test-backup-bucket'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': aws_region}
        )
        yield bucket_name


@pytest.fixture
def dynamodb_table(aws_region):
    """Fixture to create a mock DynamoDB table."""
    with mock_aws():
        dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
        table_name = 'test-table'
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table_name


@pytest.fixture
def aws_clients(s3_bucket, dynamodb_table, aws_region, monkeypatch):
    """Fixture to create mock AWS clients with environment variables."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', dynamodb_table)
    monkeypatch.setenv('REGION', aws_region)
    config = Config()
    return AWSClients(config)


@pytest.fixture
def user_pool(aws_region):
    """Fixture to create a mock Cognito user pool."""
    with mock_aws():
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        user_pool = cognito_client.create_user_pool(PoolName='testPool')
        yield user_pool['UserPool']['Id']


# Lambda Handler Tests
@mock_aws
def test_lambda_handler_backup_success(user_pool, s3_bucket, monkeypatch, aws_region):
    """Test the backup operation with a valid user pool ID."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)


    event = {
        "operation": "backup",
        "user_pool_id": user_pool
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert 'backup_location' in response_body
    assert response_body['backup_location'].startswith(f"s3://{s3_bucket}/cognito-backups/")
    assert response_body['users_backed_up'] == 0
    assert response_body['groups_backed_up'] == 0


    s3_client = boto3.client('s3', region_name=aws_region)
    backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
    backup_data = json.loads(s3_response['Body'].read())
    assert backup_data['user_pool']['Name'] == 'testPool'
    assert backup_data['users'] == []
    assert backup_data['groups'] == []


@mock_aws
def test_lambda_handler_backup_with_users_and_groups(user_pool, s3_bucket, monkeypatch, aws_region):
    """Test the backup operation with users and groups."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)


    cognito_client = boto3.client('cognito-idp', region_name=aws_region)
    cognito_client.create_group(
        GroupName='TestGroup',
        UserPoolId=user_pool,
        Description='Test group for backup'
    )
    cognito_client.admin_create_user(
        UserPoolId=user_pool,
        Username='testuser',
        UserAttributes=[
            {'Name': 'email', 'Value': 'test@example.com'},
            {'Name': 'given_name', 'Value': 'Test'},
            {'Name': 'family_name', 'Value': 'User'}
        ],
        DesiredDeliveryMediums=['EMAIL']
    )
    cognito_client.admin_add_user_to_group(
        UserPoolId=user_pool,
        Username='testuser',
        GroupName='TestGroup'
    )


    event = {
        'operation': 'backup',
        'user_pool_id': user_pool
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert response_body['users_backed_up'] == 1
    assert response_body['groups_backed_up'] == 1


    s3_client = boto3.client('s3', region_name=aws_region)
    backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
    backup_data = json.loads(s3_response['Body'].read())


    assert len(backup_data['users']) == 1
    assert len(backup_data['groups']) == 1
    assert backup_data['users'][0]['Username'] == 'testuser'
    assert backup_data['users'][0]['Groups'] == ['TestGroup']
    assert backup_data['groups'][0]['GroupName'] == 'TestGroup'


@mock_aws
def test_lambda_handler_restore_success(user_pool, s3_bucket, dynamodb_table, monkeypatch, aws_region):
    """Test the restore operation with a valid backup key and target user pool."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', dynamodb_table)
    monkeypatch.setenv('AWS_REGION', aws_region)


    source_pool_id = user_pool
    cognito_client = boto3.client('cognito-idp', region_name=aws_region)
    source_pool = cognito_client.describe_user_pool(UserPoolId=source_pool_id)
    source_pool_copy = source_pool['UserPool'].copy()
    for key in ['CreationDate', 'LastModifiedDate']:
        if key in source_pool_copy:
            source_pool_copy[key] = source_pool_copy[key].isoformat()


    backup_data = {
        'timestamp': '2025-08-13T12:00:00Z',
        'user_pool': source_pool_copy,
        'users': [
            {
                'Username': 'testuser',
                'Attributes': [
                    {'Name': 'email', 'Value': 'test@example.com'},
                    {'Name': 'sub', 'Value': 'old-sub-123'}
                ],
                'Groups': ['TestGroup'],
                'UserStatus': 'CONFIRMED'
            }
        ],
        'groups': [{'GroupName': 'TestGroup', 'Description': 'Test group'}]
    }
    backup_key = f"cognito-backups/{source_pool_id}/2025-08-13_12-00-00.json"
    s3_client = boto3.client('s3', region_name=aws_region)
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=backup_key,
        Body=json.dumps(backup_data)
    )


    target_pool = cognito_client.create_user_pool(PoolName='targetPool')
    target_pool_id = target_pool['UserPool']['Id']


    dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
    dynamodb_client.put_item(
        TableName=dynamodb_table,
        Item={
            'PK': {'S': 'u#old-sub-123'},
            'SK': {'S': 'u#old-sub-123'},
            'data': {'S': 'test-data'}
        }
    )


    event = {
        'operation': 'restore',
        'backup_key': backup_key,
        'target_user_pool_id': target_pool_id
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert response_body['user_pool_id'] == target_pool_id
    assert response_body['users_restored'] == 1
    assert response_body['groups_restored'] == 1
    assert response_body['user_group_memberships_restored'] == 1
    assert response_body['failed_users'] == []
    assert response_body['dynamodb_records_updated'] == 1
    assert response_body['dynamodb_failed_updates'] == []


@mock_aws
def test_lambda_handler_restore_missing_target_pool_id(s3_bucket, monkeypatch, aws_region):
    """Test the restore operation with missing target_user_pool_id."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)


    event = {
        'operation': 'restore',
        'backup_key': 'cognito-backups/test-pool/backup.json'
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'target_user_pool_id is required for restore operation'


@mock_aws
def test_lambda_handler_restore_nonexistent_target_pool(s3_bucket, monkeypatch, aws_region):
    """Test the restore operation with nonexistent target user pool."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)


    backup_data = {
        'timestamp': '2025-08-13T12:00:00Z',
        'user_pool': {'Name': 'TestPool'},
        'users': [],
        'groups': []
    }
    backup_key = "cognito-backups/test-pool/backup.json"
    s3_client = boto3.client('s3', region_name=aws_region)
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=backup_key,
        Body=json.dumps(backup_data)
    )


    event = {
        'operation': 'restore',
        'backup_key': backup_key,
        'target_user_pool_id': f'{aws_region}_NONEXISTENT'
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


@mock_aws
def test_lambda_handler_invalid_operation(s3_bucket, monkeypatch):
    """Test the handler with an invalid operation."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
   
    event = {'operation': 'invalid'}
    response = lambda_handler(event, None)


    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'



@mock_aws
def test_lambda_handler_missing_user_pool_id(s3_bucket, monkeypatch, aws_region):
    """Test the backup operation with missing user_pool_id."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)
    event = {'operation': 'backup'}
    response = lambda_handler(event, None)


    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'user_pool_id is required for backup operation'


@mock_aws
def test_lambda_handler_missing_backup_key(s3_bucket, monkeypatch, aws_region):
    """Test the restore operation with missing backup_key."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)
    event = {
        'operation': 'restore',
        'target_user_pool_id': f'{aws_region}_SOMEPOOL'
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'backup_key is required for restore operation'


@mock_aws
def test_lambda_handler_cognito_error(s3_bucket, monkeypatch, aws_region):
    """Test the handler when Cognito raises an error."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)
    event = {'operation': 'backup', 'user_pool_id': f'{aws_region}_invalidPool'}


    response = lambda_handler(event, None)


    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


@mock_aws
def test_lambda_handler_s3_error(monkeypatch, aws_region):
    """Test the handler when S3 operations fail."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', 'nonexistent-bucket')
    monkeypatch.setenv('AWS_REGION', aws_region)


    cognito_client = boto3.client('cognito-idp', region_name=aws_region)
    user_pool = cognito_client.create_user_pool(PoolName='testPool')
    user_pool_id = user_pool['UserPool']['Id']


    event = {
        'operation': 'backup',
        'user_pool_id': user_pool_id
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


@mock_aws
def test_lambda_handler_restore_nonexistent_backup(s3_bucket, monkeypatch, aws_region):
    """Test the restore operation with a nonexistent backup key."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    monkeypatch.setenv('AWS_REGION', aws_region)


    cognito_client = boto3.client('cognito-idp', region_name=aws_region)
    target_pool = cognito_client.create_user_pool(PoolName='targetPool')
    target_pool_id = target_pool['UserPool']['Id']


    event = {
        'operation': 'restore',
        'backup_key': 'cognito-backups/nonexistent/backup.json',
        'target_user_pool_id': target_pool_id
    }
    response = lambda_handler(event, None)


    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


# Unit Tests for Individual Classes
# @mock_aws
# def test_cognito_backup_get_users_with_groups(user_pool, aws_clients):
#     """Test CognitoBackup._get_users_with_groups."""
#     cognito_client = boto3.client('cognito-idp', region_name=aws_clients.cognito_client.meta.region_name)
#     cognito_client.create_group(GroupName='TestGroup', UserPoolId=user_pool)
#     cognito_client.admin_create_user(
#         UserPoolId=user_pool,
#         Username='testuser',
#         UserAttributes=[{'Name': 'email', 'Value': 'test@example.com'}],
#         MessageAction='SUPPRESS'
#     )
#     cognito_client.admin_add_user_to_group(
#         UserPoolId=user_pool,
#         Username='testuser',
#         GroupName='TestGroup'
#     )


#     backup = CognitoBackup(aws_clients)
#     users = backup._get_users_with_groups(user_pool)


#     assert len(users) == 1
#     assert users[0]['Username'] == 'testuser'
#     assert users[0]['Groups'] == ['TestGroup']


# @mock_aws
# def test_cognito_restore_groups(user_pool, aws_clients):
#     """Test CognitoRestore._restore_groups."""
#     groups = [{'GroupName': 'TestGroup', 'Description': 'Test group'}]
#     restore = CognitoRestore(aws_clients)
#     restored_count = restore._restore_groups(groups, user_pool)


#     assert restored_count == 1
#     groups_response = aws_clients.cognito_client.list_groups(UserPoolId=user_pool)
#     assert len(groups_response['Groups']) == 1
#     assert groups_response['Groups'][0]['GroupName'] == 'TestGroup'


@mock_aws
def test_dynamodb_update_sub(dynamodb_table, aws_clients):
    """Test DynamoDBUpdate.update_dynamodb_sub."""
    dynamodb_client = boto3.client('dynamodb', region_name=aws_clients.dynamodb_client.meta.region_name)
    dynamodb_client.put_item(
        TableName=dynamodb_table,
        Item={
            'PK': {'S': 'u#old-sub-123'},
            'SK': {'S': 'u#old-sub-123'},
            'data': {'S': 'test-data'}
        }
    )


    sub_mappings = [
        {
            'username': 'testuser',
            'old_sub': 'old-sub-123',
            'new_sub': 'new-sub-456'
        }
    ]
    update = DynamoDBUpdate(aws_clients)
    result = update.update_dynamodb_sub(sub_mappings)


    assert result['records_updated'] == 1
    assert result['failed_updates'] == []
    assert result['skipped_updates'] == 0


    response = dynamodb_client.get_item(
        TableName=dynamodb_table,
        Key={'PK': {'S': 'u#new-sub-456'}, 'SK': {'S': 'u#new-sub-456'}}
    )
    assert 'Item' in response
    assert response['Item']['data']['S'] == 'test-data'
