import json
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from aws_clients import AWSClients, logger
from dynamodb_update import DynamoDBUpdate

class CognitoRestore:
    """Handles restore operations for AWS Cognito User Pools."""
    
    def __init__(self, aws_clients: AWSClients):
        self.aws_clients = aws_clients
        self.dynamodb_update = DynamoDBUpdate(aws_clients)

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
            response = self.aws_clients.s3_client.get_object(
                Bucket=self.aws_clients.bucket_name,
                Key=backup_key
            )
            backup_data = json.loads(response['Body'].read())

            user_pool_id = self._get_user_pool(target_user_pool_id)
            restored_groups = self._restore_groups(backup_data['groups'], user_pool_id)
            restore_stats = self._restore_users(backup_data['users'], user_pool_id)

            dynamodb_stats = {'records_updated': 0, 'failed_updates': [], 'skipped_updates': 0}
            if self.aws_clients.dynamodb_table:
                dynamodb_stats = self.dynamodb_update.update_dynamodb_sub(restore_stats['sub_mappings'])
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
            self.aws_clients.cognito_client.describe_user_pool(UserPoolId=target_user_pool_id)
            logger.info("Using existing user pool: %s", target_user_pool_id)
            return target_user_pool_id
        except ClientError as exc:
            error_code = exc.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error("User pool %s does not exist", target_user_pool_id)
                raise ValueError(f"User pool {target_user_pool_id} does not exist") from exc
            logger.error("Failed to verify user pool %s: %s", target_user_pool_id, str(exc))
            raise

    def _restore_groups(self, groups: List[Dict[str, Any]], user_pool_id: str) -> int:
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

                self.aws_clients.cognito_client.create_group(**group_config)
                restored_groups += 1
                logger.info("Restored group: %s", group['GroupName'])

            except ClientError as exc:
                if 'GroupExistsException' in str(exc):
                    logger.info("Group %s already exists, skipping", group['GroupName'])
                    restored_groups += 1
                else:
                    logger.warning("Failed to restore group %s: %s", group['GroupName'], exc)

        return restored_groups

    def _restore_users(self, users: List[Dict[str, Any]], user_pool_id: str) -> Dict[str, Any]:
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
                old_sub = next((attr['Value'] for attr in user.get('Attributes', []) if attr['Name'] == 'sub'), None)

                user_attributes = [
                    {'Name': attr['Name'], 'Value': attr['Value']}
                    for attr in user.get('Attributes', [])
                    if attr['Name'] not in ['sub']
                ]

                response = self.aws_clients.cognito_client.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=username,
                    UserAttributes=user_attributes,
                    DesiredDeliveryMediums=['EMAIL']
                )

                new_sub = next(
                    (attr['Value'] for attr in response['User']['Attributes'] if attr['Name'] == 'sub'),
                    None
                )

                if old_sub and new_sub:
                    sub_mappings.append({
                        'username': username,
                        'old_sub': old_sub,
                        'new_sub': new_sub
                    })
                    logger.info("Mapped old sub %s to new sub %s for user %s", old_sub, new_sub, username)

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
                        user_response = self.aws_clients.cognito_client.admin_get_user(
                            UserPoolId=user_pool_id,
                            Username=username
                        )
                        new_sub = next(
                            (attr['Value'] for attr in user_response['UserAttributes'] if attr['Name'] == 'sub'),
                            None
                        )
                        if old_sub and new_sub:
                            sub_mappings.append({
                                'username': username,
                                'old_sub': old_sub,
                                'new_sub': new_sub
                            })
                            logger.info("Mapped old sub %s to new sub %s for existing user %s", old_sub, new_sub, username)

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

    def _restore_user_group_memberships(self, user_pool_id: str, username: str,
                                        user_groups: List[str]) -> int:
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
                self.aws_clients.cognito_client.admin_add_user_to_group(
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