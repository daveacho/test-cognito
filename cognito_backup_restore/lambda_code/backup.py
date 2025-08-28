"""Backup module for AWS Cognito User Pool operations."""
import json
from datetime import datetime, UTC
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from aws_clients import AWSClients
from config import logger

class CognitoBackup:
    """Handles backup operations for AWS Cognito User Pools."""

    def __init__(self, aws_clients: AWSClients):
        self.aws_clients = aws_clients

    def backup_user_pool(self, user_pool_id: str) -> Dict[str, Any]:
        """
        Backup Cognito User Pool users and groups (no clients).
        
        Args:
            user_pool_id: The ID of the user pool to backup
            
        Returns:
            Dict containing backup status and statistics
            
        Raises:
            ClientError: If backup operation fails
        """
        try:
            # Get user pool details
            user_pool = self.aws_clients.cognito_client.describe_user_pool(
                UserPoolId=user_pool_id
            )

            # Get users (paginated) with embedded group memberships
            users = self._get_users_with_groups(user_pool_id)

            # Get groups
            groups = self._get_groups(user_pool_id)

            # Create backup object (no clients)
            backup_data = {
                'timestamp': datetime.now(UTC).isoformat(),
                'user_pool': user_pool['UserPool'],
                'users': users,
                'groups': groups
            }

            # Save to S3
            backup_key = (
                f"cognito-backups/{user_pool_id}/"
                f"{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S')}.json"
            )

            self.aws_clients.s3_client.put_object(
                Bucket=self.aws_clients.bucket_name,
                Key=backup_key,
                Body=json.dumps(backup_data, default=str, indent=2),
                ContentType='application/json'
            )

            logger.info("Backup completed for user pool %s", user_pool_id)
            return {
                'status': 'success',
                'backup_location': f"s3://{self.aws_clients.bucket_name}/{backup_key}",
                'users_backed_up': len(users),
                'groups_backed_up': len(groups)
            }

        except ClientError as exc:
            logger.error("Backup failed for user pool %s: %s", user_pool_id, str(exc))
            raise

    def _get_users_with_groups(self, user_pool_id: str) -> List[Dict[str, Any]]:
        """
        Get all users from the user pool with their group memberships embedded.
        
        Args:
            user_pool_id: The ID of the user pool
            
        Returns:
            List of user objects with embedded group memberships
        """
        users = []
        paginator = self.aws_clients.cognito_client.get_paginator('list_users')

        for page in paginator.paginate(UserPoolId=user_pool_id):
            for user in page['Users']:
                # Enhance user object with group memberships
                username = user['Username']
                user_groups = []
                try:
                    user_groups_response = self.aws_clients.cognito_client.admin_list_groups_for_user(
                        UserPoolId=user_pool_id,
                        Username=username
                    )
                    user_groups = [
                        group['GroupName'] for group in user_groups_response['Groups']
                    ]
                    if user_groups:
                        logger.info("User %s belongs to groups: %s", username, user_groups)
                except ClientError as exc:
                    logger.warning("Could not retrieve groups for user %s: %s", username, exc)

                # Add groups to user object
                user['Groups'] = user_groups
                users.append(user)

        return users

    def _get_groups(self, user_pool_id: str) -> List[Dict[str, Any]]:
        """
        Get all groups from the user pool.
        
        Args:
            user_pool_id: The ID of the user pool
            
        Returns:
            List of group objects
        """
        groups = []
        try:
            groups_response = self.aws_clients.cognito_client.list_groups(UserPoolId=user_pool_id)
            groups = groups_response['Groups']
        except ClientError as exc:
            logger.warning("Could not retrieve groups: %s", exc)

        return groups