from typing import Dict, Any, List
from botocore.exceptions import ClientError
from aws_clients import AWSClients, logger

class DynamoDBUpdate:
    """Handles DynamoDB update operations for Cognito user sub mappings."""
    
    def __init__(self, aws_clients: AWSClients):
        self.aws_clients = aws_clients

    def update_dynamodb_sub(self, sub_mappings: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Update DynamoDB table with new user sub values using transactions.
        
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

            if old_sub == new_sub:
                logger.info("Skipping DynamoDB update for user %s: old_sub %s equals new_sub %s", username, old_sub, new_sub)
                skipped_updates += 1
                continue

            try:
                response = self.aws_clients.dynamodb_client.query(
                    TableName=self.aws_clients.dynamodb_table,
                    KeyConditionExpression='PK = :old_sub',
                    ExpressionAttributeValues={':old_sub': {'S': f'u#{old_sub}'}}
                )

                items = response.get('Items', [])
                if not items:
                    logger.info("No DynamoDB records found for user %s with PK u#%s, skipping creation", username, old_sub)
                    continue

                for item in items:
                    try:
                        old_pk = item['PK']['S']
                        old_sk = item['SK']['S']
                        
                        new_item = {k: v for k, v in item.items()}
                        new_item['PK'] = {'S': f'u#{new_sub}'}

                        if old_sk.startswith('u#'):
                            new_item['SK'] = {'S': f'u#{new_sub}'}

                        self.aws_clients.dynamodb_client.transact_write_items(
                            TransactItems=[
                                {
                                    'Put': {
                                        'TableName': self.aws_clients.dynamodb_table,
                                        'Item': new_item
                                    }
                                },
                                {
                                    'Delete': {
                                        'TableName': self.aws_clients.dynamodb_table,
                                        'Key': {
                                            'PK': {'S': old_pk},
                                            'SK': {'S': old_sk}
                                        }
                                    }
                                }
                            ]
                        )
                        updated_records += 1
                        logger.info("Updated DynamoDB record for user %s: PK u#%s -> u#%s, SK %s -> %s",
                                    username, old_sub, new_sub, old_sk, new_item['SK']['S'])
                    except ClientError as exc:
                        logger.warning("Failed to update DynamoDB record for user %s (PK u#%s -> u#%s, SK %s): %s",
                                      username, old_sub, new_sub, old_sk, exc)
                        failed_updates.append({
                            'username': username,
                            'old_sub': old_sub,
                            'sk': old_sk,
                            'error': str(exc)
                        })
            except ClientError as exc:
                logger.warning("Failed to query DynamoDB for user %s (PK u#%s): %s", username, old_sub, exc)
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