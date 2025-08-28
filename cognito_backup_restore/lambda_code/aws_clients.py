"""AWS client initialization module for Cognito backup/restore operations."""
import boto3
from .config import Config

class AWSClients:
    """Manages AWS client initialization for Cognito, S3, and DynamoDB."""

    def __init__(self, config: Config):
        self.cognito_client = boto3.client('cognito-idp', region_name=config.region)
        self.s3_client = boto3.client('s3', region_name=config.region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=config.region)
        self.bucket_name = config.backup_bucket_name
        self.dynamodb_table = config.dynamodb_table_name