"""Add UUID fields to test_files and testcases

Revision ID: add_uuid_fields
Revises: 
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_uuid_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add UUID columns to test_files and testcases tables."""
    
    # Add test_uid column to test_files
    op.add_column('test_files', 
                  sa.Column('test_uid', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add testcase_uid column to testcases
    op.add_column('testcases', 
                  sa.Column('testcase_uid', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate existing rows with UUIDs
    op.execute("""
        UPDATE test_files 
        SET test_uid = gen_random_uuid() 
        WHERE test_uid IS NULL
    """)
    
    op.execute("""
        UPDATE testcases 
        SET testcase_uid = gen_random_uuid() 
        WHERE testcase_uid IS NULL
    """)
    
    # Make columns non-nullable
    op.alter_column('test_files', 'test_uid', nullable=False)
    op.alter_column('testcases', 'testcase_uid', nullable=False)
    
    # Add unique constraints and indexes
    op.create_unique_constraint('uq_test_files_test_uid', 'test_files', ['test_uid'])
    op.create_index('ix_test_files_test_uid', 'test_files', ['test_uid'])
    
    op.create_unique_constraint('uq_testcases_testcase_uid', 'testcases', ['testcase_uid'])
    op.create_index('ix_testcases_testcase_uid', 'testcases', ['testcase_uid'])


def downgrade() -> None:
    """Remove UUID columns from test_files and testcases tables."""
    
    # Drop indexes and constraints
    op.drop_index('ix_testcases_testcase_uid', table_name='testcases')
    op.drop_constraint('uq_testcases_testcase_uid', 'testcases', type_='unique')
    
    op.drop_index('ix_test_files_test_uid', table_name='test_files')
    op.drop_constraint('uq_test_files_test_uid', 'test_files', type_='unique')
    
    # Drop columns
    op.drop_column('testcases', 'testcase_uid')
    op.drop_column('test_files', 'test_uid')
