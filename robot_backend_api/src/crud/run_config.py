"""
CRUD operations for run configurations.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from models.run_config import RunConfig
from schemas.run_config import RunConfigCreate, RunConfigUpdate


# PUBLIC_INTERFACE
def get_run_config(db: Session, config_id: int) -> Optional[RunConfig]:
    """
    Get a run configuration by ID.
    
    Args:
        db: Database session
        config_id: Configuration ID
        
    Returns:
        Optional[RunConfig]: Configuration if found, None otherwise
    """
    return db.query(RunConfig).filter(RunConfig.id == config_id).first()


# PUBLIC_INTERFACE
def get_run_configs(db: Session, skip: int = 0, limit: int = 100) -> List[RunConfig]:
    """
    Get a list of run configurations.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[RunConfig]: List of configurations
    """
    return db.query(RunConfig).offset(skip).limit(limit).all()


# PUBLIC_INTERFACE
def create_run_config(db: Session, config: RunConfigCreate) -> RunConfig:
    """
    Create a new run configuration.
    
    Args:
        db: Database session
        config: Configuration creation data
        
    Returns:
        RunConfig: Created configuration
    """
    db_config = RunConfig(**config.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


# PUBLIC_INTERFACE
def update_run_config(db: Session, config_id: int, config_update: RunConfigUpdate) -> Optional[RunConfig]:
    """
    Update a run configuration.
    
    Args:
        db: Database session
        config_id: Configuration ID
        config_update: Update data
        
    Returns:
        Optional[RunConfig]: Updated configuration if found, None otherwise
    """
    db_config = get_run_config(db, config_id)
    if not db_config:
        return None
    
    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config


# PUBLIC_INTERFACE
def delete_run_config(db: Session, config_id: int) -> bool:
    """
    Delete a run configuration.
    
    Args:
        db: Database session
        config_id: Configuration ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    db_config = get_run_config(db, config_id)
    if not db_config:
        return False
    
    db.delete(db_config)
    db.commit()
    return True
