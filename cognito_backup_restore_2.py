"""
AWS Cognito User Pool backup and restore functionality.

This module provides a comprehensive solution for backing up and restoring
AWS Cognito User Pools, including users, groups, and group memberships.
It also handles DynamoDB updates for user sub mappings during restoration.
"""
import json
import logging
import os
from datetime import datetime, UTC
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CognitoBackupRestore:
    """
    Handles backup and restore operations for AWS Cognito User Pools.


    This class provides methods to back up user pool data (users and groups)
    to S3 and restore from S3 backups.
    """

    def __init__(self):
        """Initialize the CognitoBackupRestore with AWS clients."""
        region = os.environ.get('REGION', 'eu-west-2')
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        self.bucket_name = os.environ.get('BACKUP_BUCKET_NAME')
        self.dynamodb_table = os.environ.get('DYNAMODB_TABLE_NAME')

    def backup_user_pool(self, user_pool_id: str) -> Dict[str, Any]:
        """
        Backup Cognito User Pool users and groups only.


        Args:
            user_pool_id: The ID of the user pool to back up


        Returns:
            Dict containing backup status and statistics


        Raises:
            Exception: If backup operation fails
        """
        try:
            # Get user pool details
            user_pool = self.cognito_client.describe_user_pool(
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

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=backup_key,
                Body=json.dumps(backup_data, default=str, indent=2),
                ContentType='application/json'
            )

            logger.info("Backup completed for user pool %s", user_pool_id)
            return {
                'status': 'success',
                'backup_location': f"s3://{self.bucket_name}/{backup_key}",
                'users_backed_up': len(users),
                'groups_backed_up': len(groups)
            }


        except ClientError as exc:
            logger.error("Backup failed for user pool %s: %s", user_pool_id, str(exc))
            raise

    def _get_users_with_groups(self, user_pool_id: str) -> list:
        """
        Get all users from the user pool with their group memberships embedded.


        Args:
            user_pool_id: The ID of the user pool


        Returns:
            List of user objects with embedded group memberships
        """
        users = []
        paginator = self.cognito_client.get_paginator('list_users')

        for page in paginator.paginate(UserPoolId=user_pool_id):
            for user in page['Users']:
                # Enhance user object with group memberships
                username = user['Username']
                user_groups = []
                try:
                    user_groups_response = self.cognito_client.admin_list_groups_for_user(
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

    def _get_groups(self, user_pool_id: str) -> list:
        """
        Get all groups from the user pool.


        Args:
            user_pool_id: The ID of the user pool


        Returns:
            List of group objects
        """
        groups = []
        try:
            groups_response = self.cognito_client.list_groups(UserPoolId=user_pool_id)
            groups = groups_response['Groups']
        except ClientError as exc:
            logger.warning("Could not retrieve groups: %s", exc)

        return groups

    def restore_user_pool(self, backup_key: str, target_user_pool_id: str = None) -> Dict[str, Any]:
        """
        Restore Cognito User Pool from a backup in S3.


        Args:
            backup_key: S3 key of the backup file
            target_user_pool_id: The ID of the target user pool for restoration


        Returns:
            Dict containing restoration status and statistics
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=backup_key)
            backup_data = json.loads(response['Body'].read())

            user_pool_id = self._get_user_pool(target_user_pool_id)
            restored_groups = self._restore_groups(backup_data['groups'], user_pool_id)
            restore_stats = self._restore_users(backup_data['users'], user_pool_id)

            dynamodb_stats = {'records_updated': 0, 'failed_updates': []}
            if self.dynamodb_table:
                dynamodb_stats = self._update_dynamodb_sub(restore_stats['sub_mappings'])
            else:
                logger.warning("DYNAMODB_TABLE_NAME not set, skipping DynamoDB updates")

            logger.info("Restore completed for user pool %s", user_pool_id)
            return {
                'status': 'success',
                'user_pool_id': user_pool_id,
                'users_restored': restore_stats['users_restored'],
                'groups_restored': restored_groups,
                'user_group_memberships_restored': restore_stats['memberships_restored'],
                'failed_users': restore_stats['failed_users'],
                'dynamodb_records_updated': dynamodb_stats['records_updated'],
                'dynamodb_failed_updates': dynamodb_stats['failed_updates'],
                'backup_timestamp': backup_data['timestamp']
            }


        except (ClientError, ValueError) as exc:
            logger.error("Restore failed: %s", str(exc))
            raise

    def _get_user_pool(self, target_user_pool_id: str = None) -> str:
        """
        Get existing user pool ID for restoration.


        Args:
            target_user_pool_id: Target user pool ID (required)


        Returns:
            User pool ID to use for restoration


        Raises:
            ValueError: If target_user_pool_id is not provided or pool doesn't exist
        """
        if not target_user_pool_id:
            raise ValueError("target_user_pool_id is required for restoration")

        try:
            self.cognito_client.describe_user_pool(UserPoolId=target_user_pool_id)
            logger.info("Using existing user pool: %s", target_user_pool_id)
            return target_user_pool_id
        except ClientError as exc:
            error_code = exc.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error("User pool %s does not exist", target_user_pool_id)
                raise ValueError(f"User pool {target_user_pool_id} does not exist") from exc
            logger.error("Failed to verify user pool %s: %s", target_user_pool_id, str(exc))
            raise

    def _restore_groups(self, groups: list, user_pool_id: str) -> int:
        """
        Restore groups to the user pool.


        Args:
            groups: List of group objects to restore
            user_pool_id: Target user pool ID


        Returns:
            Number of groups restored
        """
        restored_groups = 0
        for group in groups:
            try:
                group_config = {
                    'GroupName': group['GroupName'],
                    'UserPoolId': user_pool_id
                }
                if 'Description' in group:
                    group_config['Description'] = group['Description']
                if 'Precedence' in group:
                    group_config['Precedence'] = group['Precedence']

                self.cognito_client.create_group(**group_config)
                restored_groups += 1
                logger.info("Restored group: %s", group['GroupName'])


            except ClientError as exc:
                if 'GroupExistsException' in str(exc):
                    logger.info("Group %s already exists, skipping", group['GroupName'])
                    restored_groups += 1
                else:
                    logger.warning("Failed to restore group %s: %s", group['GroupName'], exc)

        return restored_groups

    def _restore_users(self, users: list, user_pool_id: str) -> Dict[str, Any]:
        """
        Restore users to the user pool with their group memberships and track sub mappings.


        Args:
            users: List of user objects to restore
            user_pool_id: Target user pool ID


        Returns:
            Dict containing restoration statistics and sub mappings
        """
        restored_users = 0
        restored_memberships = 0
        failed_users = []
        sub_mappings = []

        for user in users:
            try:
                username = user['Username']
                user_groups = user.get('Groups', [])
                old_sub = next(
                    (attr['Value'] for attr in user.get('Attributes', [])
                     if attr['Name'] == 'sub'), None
                )

                user_attributes = [
                    {'Name': attr['Name'], 'Value': attr['Value']}
                    for attr in user.get('Attributes', [])
                    if attr['Name'] not in ['sub']
                ]

                response = self.cognito_client.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=username,
                    UserAttributes=user_attributes,
                    DesiredDeliveryMediums=['EMAIL']
                )

                new_sub = next(
                    (attr['Value'] for attr in response['User']['Attributes']
                     if attr['Name'] == 'sub'),
                    None
                )

                if old_sub and new_sub:
                    sub_mappings.append({
                        'username': username,
                        'old_sub': old_sub,
                        'new_sub': new_sub
                    })
                    logger.info("Mapped old sub %s to new sub %s for user %s",
                                old_sub, new_sub, username)

                restored_users += 1
                logger.info("Restored user: %s", username)
                restored_memberships += self._restore_user_group_memberships(
                    user_pool_id, username, user_groups
                )


            except ClientError as exc:
                if 'UsernameExistsException' in str(exc):
                    logger.info("User %s already exists, skipping user creation", username)
                    restored_users += 1

                    try:
                        user_response = self.cognito_client.admin_get_user(
                            UserPoolId=user_pool_id,
                            Username=username
                        )
                        new_sub = next(
                            (attr['Value'] for attr in user_response['UserAttributes']
                             if attr['Name'] == 'sub'),
                            None
                        )
                        if old_sub and new_sub:
                            sub_mappings.append({
                                'username': username,
                                'old_sub': old_sub,
                                'new_sub': new_sub
                            })
                            logger.info("Mapped old sub %s to new sub %s for existing user %s",
                                        old_sub, new_sub, username)

                        restored_memberships += self._restore_user_group_memberships(
                            user_pool_id, username, user_groups
                        )
                    except ClientError as e:
                        logger.warning("Failed to get user %s details: %s", username, e)
                        failed_users.append(username)
                else:
                    logger.warning("Failed to restore user %s: %s", username, exc)
                    failed_users.append(username)

        return {
            'users_restored': restored_users,
            'memberships_restored': restored_memberships,
            'failed_users': failed_users,
            'sub_mappings': sub_mappings
        }

    def _update_dynamodb_sub(self, sub_mappings: list) -> Dict[str, Any]:
        """
        Update DynamoDB table with new user sub values, skipping if old_sub equals new_sub.


        Args:
            sub_mappings: List of mappings containing old_sub, new_sub, and username


        Returns:
            Dict containing update statistics
        """
        updated_records = 0
        failed_updates = []
        skipped_updates = 0

        for mapping in sub_mappings:
            old_sub = mapping['old_sub']
            new_sub = mapping['new_sub']
            username = mapping['username']

            # Skip update if old_sub equals new_sub
            if old_sub == new_sub:
                logger.info(
                    "Skipping DynamoDB update for user %s: old_sub %s equals new_sub %s",
                    username, old_sub, new_sub
                )
                skipped_updates += 1
                continue

            try:
                # Query for items with PK as u#<old_sub>
                response = self.dynamodb_client.query(
                    TableName=self.dynamodb_table,
                    KeyConditionExpression='PK = :old_sub',
                    ExpressionAttributeValues={':old_sub': {'S': f'u#{old_sub}'}}
                )

                items = response.get('Items', [])
                if not items:
                    logger.info(
                        "No DynamoDB records found for user %s with PK u#%s, skipping creation",
                        username, old_sub
                    )
                    continue

                for item in items:
                    try:
                        # Get the SK from the item (could be u#<sub> or another value)
                        existing_sk = item['SK']['S']

                        # Delete the old item
                        self.dynamodb_client.delete_item(
                            TableName=self.dynamodb_table,
                            Key={
                                'PK': {'S': f'u#{old_sub}'},
                                'SK': {'S': existing_sk}
                            }
                        )

                        # Create a new item with the new sub, preserving SK
                        new_item = {
                            'PK': {'S': f'u#{new_sub}'},
                            'SK': {'S': existing_sk}
                        }
                        # Preserve other attributes if they exist
                        for attr in ['asID', 'dT', 'grpID', 'owID']:
                            if attr in item and item[attr].get('S'):
                                new_item[attr] = {'S': item[attr]['S']}

                        self.dynamodb_client.put_item(
                            TableName=self.dynamodb_table,
                            Item=new_item
                        )
                        updated_records += 1
                        logger.info(
                            "Updated DynamoDB record for user %s: PK u#%s -> u#%s, SK %s",
                            username, old_sub, new_sub, existing_sk
                        )
                    except ClientError as exc:
                        logger.warning(
                            "Failed to update DynamoDB record for user %s "
                            "(PK u#%s -> u#%s, SK %s): %s",
                            username, old_sub, new_sub, existing_sk, exc
                        )
                        failed_updates.append({
                            'username': username,
                            'old_sub': old_sub,
                            'sk': existing_sk,
                            'error': str(exc)
                        })
            except ClientError as exc:
                logger.warning("Failed to query DynamoDB for user %s (PK u#%s): %s",
                               username, old_sub, exc)
                failed_updates.append({
                    'username': username,
                    'old_sub': old_sub,
                    'error': str(exc)
                })

        return {
            'records_updated': updated_records,
            'failed_updates': failed_updates,
            'skipped_updates': skipped_updates
        }

    def _restore_user_group_memberships(self, user_pool_id: str, username: str,
                                        user_groups: list) -> int:
        """
        Restore group memberships for a specific user.


        Args:
            user_pool_id: Target user pool ID
            username: Username to add to groups
            user_groups: List of group names the user should belong to


        Returns:
            Number of group memberships restored
        """
        memberships_restored = 0
        for group_name in user_groups:
            try:
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=user_pool_id,
                    Username=username,
                    GroupName=group_name
                )
                memberships_restored += 1
                logger.info("Added user %s to group %s", username, group_name)


            except ClientError as exc:
                logger.warning("Failed to add user %s to group %s: %s",
                               username, group_name, exc)

        return memberships_restored

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
        backup_restore = CognitoBackupRestore()
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

            result = backup_restore.backup_user_pool(user_pool_id)
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

            result = backup_restore.restore_user_pool(backup_key, target_user_pool_id)
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