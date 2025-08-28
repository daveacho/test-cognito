"""Lambda handler module for Cognito backup and restore operations."""
import json
from typing import Dict, Any
from botocore.exceptions import ClientError
from .config import Config, logger
from .aws_clients import AWSClients
from .backup import CognitoBackup
from .restore import CognitoRestore

def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    """
    Main Lambda handler for Cognito backup and restore operations.

    Args:
        event: Lambda event containing operation details
        _context: Lambda context (unused, prefixed with underscore)

    Returns:
        Dict containing HTTP response with status and body
    """
    try:
        config = Config()
        config.validate()
        aws_clients = AWSClients(config)
        operation = event.get('operation')

        if operation == 'backup':
            user_pool_id = event.get('user_pool_id')
            if not user_pool_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'user_pool_id is required for backup operation'
                    })
                }

            backup_service = CognitoBackup(aws_clients)
            result = backup_service.backup_user_pool(user_pool_id)
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }

        if operation == 'restore':
            backup_key = event.get('backup_key')
            target_user_pool_id = event.get('target_user_pool_id')

            if not backup_key:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'backup_key is required for restore operation'
                    })
                }

            if not target_user_pool_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'target_user_pool_id is required for restore operation'
                    })
                }

            restore_service = CognitoRestore(aws_clients)
            result = restore_service.restore_user_pool(backup_key, target_user_pool_id)
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }

        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid operation. Use "backup" or "restore"'
            })
        }

    except (ClientError, ValueError) as exc:
        logger.error("Lambda execution failed: %s", str(exc))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(exc)})
        }