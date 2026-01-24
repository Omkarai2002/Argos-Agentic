"""
Database operations for prompt completion layer.
Stores prompt validation and completion results in database.
"""

import psycopg
from datetime import datetime
from typing import Optional
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG
from .models import PromptCompletionResponse, CompletionCheckResult

logger = logging.getLogger(__name__)


class PromptCompletionDB:
    """Handle database operations for prompt completion."""
    
    def __init__(self):
        """Initialize database connection config."""
        self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]
    
    def get_connection(self):
        """Get database connection."""
        try:
            conn = psycopg.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def save_prompt_completion(
        self,
        response: PromptCompletionResponse,
        user_id: int,
        site_id: int,
        org_id: int,
        status: str = None
    ) -> int:
        """
        Save prompt completion result to database.
        
        Args:
            response: PromptCompletionResponse object
            user_id: User ID
            site_id: Site ID
            org_id: Organization ID
            status: Status (APPROVED, REJECTED, PENDING)
                   If None, derived from completion result
        
        Returns:
            ID of inserted record
        """
        try:
            # Determine status from completion result if not provided
            if status is None:
                if response.completion_result.is_complete:
                    status = "APPROVED"
                else:
                    status = "REJECTED"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert record
            query = """
            INSERT INTO prompt_conversations 
            (user_id, status, initial_prompt, site_id, org_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            
            cursor.execute(
                query,
                (
                    user_id,
                    status,
                    response.original_prompt,
                    site_id,
                    org_id,
                    datetime.utcnow()
                )
            )
            
            record_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Saved prompt completion to DB: record_id={record_id}")
            
            cursor.close()
            conn.close()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            raise
    
    def update_prompt_final(
        self,
        record_id: int,
        final_prompt: str,
        status: str = "APPROVED"
    ) -> bool:
        """
        Update a record with final prompt and status.
        
        Args:
            record_id: ID of record to update
            final_prompt: Final processed prompt
            status: Final status
        
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE prompt_conversations 
            SET final_prompt = %s, status = %s, updated_at = %s
            WHERE id = %s;
            """
            
            cursor.execute(
                query,
                (
                    final_prompt,
                    status,
                    datetime.utcnow(),
                    record_id
                )
            )
            
            conn.commit()
            logger.info(f"Updated prompt record: {record_id}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating record: {str(e)}")
            raise
        
    def update_status_of_prompt(self, record_id: int, status: str) -> bool:
        """
        Update the status of a prompt record.
        
        Args:
            record_id: ID of record to update
            status: New status value
        
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE prompt_conversations 
            SET status = %s, updated_at = %s
            WHERE id = %s;
            """
            
            cursor.execute(
                query,
                (
                    status,
                    datetime.utcnow(),
                    record_id
                )
            )
            
            conn.commit()
            logger.info(f"Updated status of prompt record: {record_id} to {status}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating status of record: {str(e)}")
            raise
    def close_prompt(self, record_id: int) -> bool:
        """
        Mark a prompt as ended.
        
        Args:
            record_id: ID of record to close
        
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE prompt_conversations 
            SET ended_at = %s
            WHERE id = %s;
            """
            
            cursor.execute(query, (datetime.utcnow(), record_id))
            
            conn.commit()
            logger.info(f"Closed prompt record: {record_id}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing record: {str(e)}")
            raise
    
    def get_prompt_record(self, record_id: int) -> dict:
        """
        Retrieve a prompt record from database.
        
        Args:
            record_id: ID of record to retrieve
        
        Returns:
            Dictionary with record data
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT id, user_id, status, initial_prompt, final_prompt,
                   site_id, org_id, created_at, updated_at, ended_at
            FROM prompt_conversations 
            WHERE id = %s;
            """
            
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "user_id": row[1],
                "status": row[2],
                "initial_prompt": row[3],
                "final_prompt": row[4],
                "site_id": row[5],
                "org_id": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "ended_at": row[9]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving record: {str(e)}")
            raise
