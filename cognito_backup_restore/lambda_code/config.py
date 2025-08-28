"""Configuration module for Cognito backup/restore system."""
import os
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Config:
    """Handles configuration and environment variables for the Cognito backup/restore system."""

    def __init__(self):
        self.region: str = os.environ.get('REGION', 'eu-west-2')
        self.backup_bucket_name: Optional[str] = os.environ.get('BACKUP_BUCKET_NAME')
        self.dynamodb_table_name: Optional[str] = os.environ.get('DYNAMODB_TABLE_NAME')

    def validate(self) -> None:
        """Validate required configuration parameters."""
        if not self.backup_bucket_name:
            logger.error("BACKUP_BUCKET_NAME environment variable is not set")
            raise ValueError("BACKUP_BUCKET_NAME is required")
        if not self.dynamodb_table_name:
            logger.warning("DYNAMODB_TABLE_NAME environment variable is not set")