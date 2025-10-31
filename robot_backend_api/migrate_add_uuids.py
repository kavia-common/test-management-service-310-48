"""
Database migration script to add UUID fields to existing test_files and testcases tables.

This script should be run once to migrate existing databases to include UUID fields.
For new databases, the UUID fields will be created automatically via init_db().
"""
import logging
from sqlalchemy import text, inspect
from core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        
    Returns:
        bool: True if column exists, False otherwise
    """
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_add_uuids():
    """
    Add UUID fields to test_files and testcases tables if they don't exist.
    
    This migration:
    1. Adds test_uid column to test_files (if not exists)
    2. Adds testcase_uid column to testcases (if not exists)
    3. Populates existing rows with generated UUIDs
    4. Adds unique constraints and indexes
    """
    logger.info("Starting UUID migration...")
    
    with engine.connect() as conn:
        # Check if migrations are needed
        test_uid_exists = check_column_exists('test_files', 'test_uid')
        testcase_uid_exists = check_column_exists('testcases', 'testcase_uid')
        
        if test_uid_exists and testcase_uid_exists:
            logger.info("UUID columns already exist. No migration needed.")
            return
        
        # Migrate test_files table
        if not test_uid_exists:
            logger.info("Adding test_uid column to test_files...")
            
            # Add column as nullable first
            conn.execute(text("""
                ALTER TABLE test_files 
                ADD COLUMN IF NOT EXISTS test_uid UUID
            """))
            conn.commit()
            
            # Populate existing rows with UUIDs
            logger.info("Populating test_uid for existing rows...")
            conn.execute(text("""
                UPDATE test_files 
                SET test_uid = gen_random_uuid() 
                WHERE test_uid IS NULL
            """))
            conn.commit()
            
            # Make column non-nullable
            logger.info("Setting test_uid as non-nullable...")
            conn.execute(text("""
                ALTER TABLE test_files 
                ALTER COLUMN test_uid SET NOT NULL
            """))
            conn.commit()
            
            # Add unique constraint and index
            logger.info("Adding unique constraint and index for test_uid...")
            try:
                conn.execute(text("""
                    ALTER TABLE test_files 
                    ADD CONSTRAINT uq_test_files_test_uid UNIQUE (test_uid)
                """))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add unique constraint (may already exist): {e}")
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_test_files_test_uid 
                    ON test_files (test_uid)
                """))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add index (may already exist): {e}")
            
            logger.info("✓ test_uid migration completed")
        else:
            logger.info("test_uid column already exists, skipping...")
        
        # Migrate testcases table
        if not testcase_uid_exists:
            logger.info("Adding testcase_uid column to testcases...")
            
            # Add column as nullable first
            conn.execute(text("""
                ALTER TABLE testcases 
                ADD COLUMN IF NOT EXISTS testcase_uid UUID
            """))
            conn.commit()
            
            # Populate existing rows with UUIDs
            logger.info("Populating testcase_uid for existing rows...")
            conn.execute(text("""
                UPDATE testcases 
                SET testcase_uid = gen_random_uuid() 
                WHERE testcase_uid IS NULL
            """))
            conn.commit()
            
            # Make column non-nullable
            logger.info("Setting testcase_uid as non-nullable...")
            conn.execute(text("""
                ALTER TABLE testcases 
                ALTER COLUMN testcase_uid SET NOT NULL
            """))
            conn.commit()
            
            # Add unique constraint and index
            logger.info("Adding unique constraint and index for testcase_uid...")
            try:
                conn.execute(text("""
                    ALTER TABLE testcases 
                    ADD CONSTRAINT uq_testcases_testcase_uid UNIQUE (testcase_uid)
                """))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add unique constraint (may already exist): {e}")
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_testcases_testcase_uid 
                    ON testcases (testcase_uid)
                """))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add index (may already exist): {e}")
            
            logger.info("✓ testcase_uid migration completed")
        else:
            logger.info("testcase_uid column already exists, skipping...")
    
    logger.info("UUID migration completed successfully!")


if __name__ == "__main__":
    try:
        migrate_add_uuids()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
