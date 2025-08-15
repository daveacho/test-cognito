import pytest
import json
import boto3
from moto import mock_aws
from cognito_backup_restore.cognito_backup_restore import lambda_handler


@pytest.fixture
def lambda_event():
    """Fixture for a sample Lambda event."""
    return {
        "operation": "backup",
        "user_pool_id": None  # Will be set in test
    }


@pytest.fixture
def s3_bucket():
    """Fixture to create a mock S3 bucket."""
    with mock_aws():
        s3_client = boto3.client('s3', region_name='eu-west-2')
        bucket_name = 'test-backup-bucket'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'}
        )
        yield bucket_name


@mock_aws
def test_lambda_handler_backup_success(lambda_event, s3_bucket, monkeypatch):
    """Test the backup operation with a valid user pool ID."""
    # Mock environment variable
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    # Create a mock user pool
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
    user_pool = cognito_client.create_user_pool(PoolName='testPool')
    user_pool_id = user_pool['UserPool']['Id']  # Get actual mock ID
    lambda_event['user_pool_id'] = user_pool_id  # Update event with correct ID

    # Call the Lambda handler
    response = lambda_handler(lambda_event, None)

    # Verify response
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert 'backup_location' in response_body
    assert response_body['backup_location'].startswith(f"s3://{s3_bucket}/cognito-backups/")
    assert response_body['users_backed_up'] == 0  # No users in mock
    assert response_body['groups_backed_up'] == 0  # No groups in mock

    # Verify S3 upload
    s3_client = boto3.client('s3', region_name='eu-west-2')
    backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
    backup_data = json.loads(s3_response['Body'].read())
    assert backup_data['user_pool']['Name'] == 'testPool'
    assert backup_data['users'] == []
    assert backup_data['groups'] == []


@mock_aws
def test_lambda_handler_backup_with_users_and_groups(s3_bucket, monkeypatch):
    """Test the backup operation with users and groups."""
    # Mock environment variable
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    # Create a mock user pool with users and groups
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
    user_pool = cognito_client.create_user_pool(PoolName='testPoolWithData')
    user_pool_id = user_pool['UserPool']['Id']

    # Create a group
    cognito_client.create_group(
        GroupName='TestGroup',
        UserPoolId=user_pool_id,
        Description='Test group for backup'
    )

    # Create a user
    cognito_client.admin_create_user(
        UserPoolId=user_pool_id,
        Username='testuser',
        UserAttributes=[
            {'Name': 'email', 'Value': 'test@example.com'},
            {'Name': 'given_name', 'Value': 'Test'},
            {'Name': 'family_name', 'Value': 'User'}
        ],
        MessageAction='SUPPRESS'
    )

    # Add user to group
    cognito_client.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username='testuser',
        GroupName='TestGroup'
    )

    # Call the Lambda handler
    event = {
        'operation': 'backup',
        'user_pool_id': user_pool_id
    }
    response = lambda_handler(event, None)

    # Verify response
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert response_body['users_backed_up'] == 1
    assert response_body['groups_backed_up'] == 1

    # Verify backup data
    s3_client = boto3.client('s3', region_name='eu-west-2')
    backup_key = response_body['backup_location'].replace(f"s3://{s3_bucket}/", "")
    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=backup_key)
    backup_data = json.loads(s3_response['Body'].read())

    assert len(backup_data['users']) == 1
    assert len(backup_data['groups']) == 1
    assert backup_data['users'][0]['Username'] == 'testuser'
    assert backup_data['users'][0]['Groups'] == ['TestGroup']
    assert backup_data['groups'][0]['GroupName'] == 'TestGroup'


@mock_aws
def test_lambda_handler_restore_success(s3_bucket, monkeypatch):
    """Test the restore operation with a valid backup key and target user pool."""
    # Mock environment variable
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    # Create a mock source user pool and backup data
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
    source_pool = cognito_client.create_user_pool(PoolName='sourcePool')
    source_pool_id = source_pool['UserPool']['Id']

    # Convert datetime fields to strings to avoid JSON serialization issues
    source_pool_copy = source_pool['UserPool'].copy()
    for key in ['CreationDate', 'LastModifiedDate']:
        if key in source_pool_copy:
            source_pool_copy[key] = source_pool_copy[key].isoformat()

    # Create a backup in S3
    backup_data = {
        'timestamp': '2025-08-13T12:00:00Z',
        'user_pool': source_pool_copy,
        'users': [
            {
                'Username': 'testuser',
                'Attributes': [{'Name': 'email', 'Value': 'test@example.com'}],
                'Groups': ['TestGroup'],
                'UserStatus': 'CONFIRMED'
            }
        ],
        'groups': [{'GroupName': 'TestGroup'}]
    }
    backup_key = f"cognito-backups/{source_pool_id}/2025-08-13_12-00-00.json"
    s3_client = boto3.client('s3', region_name='eu-west-2')
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=backup_key,
        Body=json.dumps(backup_data)
    )

    # Create a mock target user pool
    target_pool = cognito_client.create_user_pool(PoolName='targetPool')
    target_pool_id = target_pool['UserPool']['Id']  # Get actual mock ID

    # Call the Lambda handler for restore
    event = {
        'operation': 'restore',
        'backup_key': backup_key,
        'target_user_pool_id': target_pool_id  # Required parameter
    }
    response = lambda_handler(event, None)

    # Verify response
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['status'] == 'success'
    assert response_body['user_pool_id'] == target_pool_id
    assert response_body['users_restored'] == 1
    assert response_body['groups_restored'] == 1
    assert response_body['user_group_memberships_restored'] == 1
    assert response_body['failed_users'] == []


@mock_aws
def test_lambda_handler_restore_missing_target_pool_id(s3_bucket, monkeypatch):
    """Test the restore operation with missing target_user_pool_id."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    event = {
        'operation': 'restore',
        'backup_key': 'cognito-backups/test-pool/backup.json'
        # Missing target_user_pool_id
    }
    response = lambda_handler(event, None)

    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'target_user_pool_id is required for restore operation'


@mock_aws
def test_lambda_handler_restore_nonexistent_target_pool(s3_bucket, monkeypatch):
    """Test the restore operation with nonexistent target user pool."""
    # Mock environment variable
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    # Create backup data in S3
    backup_data = {
        'timestamp': '2025-08-13T12:00:00Z',
        'user_pool': {'Name': 'TestPool'},
        'users': [],
        'groups': []
    }
    backup_key = "cognito-backups/test-pool/backup.json"
    s3_client = boto3.client('s3', region_name='eu-west-2')
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=backup_key,
        Body=json.dumps(backup_data)
    )

    # Call with nonexistent target pool ID
    event = {
        'operation': 'restore',
        'backup_key': backup_key,
        'target_user_pool_id': 'eu-west-2_NONEXISTENT'
    }
    response = lambda_handler(event, None)

    # Should return 500 error due to nonexistent pool
    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


@mock_aws
def test_lambda_handler_invalid_operation():
    """Test the handler with an invalid operation."""
    event = {'operation': 'invalid'}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'Invalid operation. Use "backup" or "restore"'


@mock_aws
def test_lambda_handler_missing_user_pool_id(s3_bucket, monkeypatch):
    """Test the backup operation with missing user_pool_id."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    event = {'operation': 'backup'}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'user_pool_id is required for backup operation'


@mock_aws
def test_lambda_handler_missing_backup_key(s3_bucket, monkeypatch):
    """Test the restore operation with missing backup_key."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    event = {
        'operation': 'restore',
        'target_user_pool_id': 'eu-west-2_SOMEPOOL'
    }
    response = lambda_handler(event, None)

    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'backup_key is required for restore operation'


@mock_aws
def test_lambda_handler_cognito_error(s3_bucket, monkeypatch):
    """Test the handler when Cognito raises an error."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)
    event = {'operation': 'backup', 'user_pool_id': 'eu-west-2_invalidPool'}

    response = lambda_handler(event, None)

    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])


@mock_aws
def test_lambda_handler_s3_error(monkeypatch):
    """Test the handler when S3 operations fail."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', 'nonexistent-bucket')

    # Create a mock user pool
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
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
def test_lambda_handler_restore_nonexistent_backup(s3_bucket, monkeypatch):
    """Test the restore operation with a nonexistent backup key."""
    monkeypatch.setenv('BACKUP_BUCKET_NAME', s3_bucket)

    # Create a target user pool
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-2')
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
