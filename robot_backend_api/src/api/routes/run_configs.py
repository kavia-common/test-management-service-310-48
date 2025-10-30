"""
API routes for run configuration management.
Provides endpoints for managing reusable test execution configurations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from schemas.run_config import RunConfigResponse, RunConfigCreate, RunConfigUpdate
from crud import run_config as crud_run_config

router = APIRouter(prefix="/run-configs", tags=["Run Configurations"])


# PUBLIC_INTERFACE
@router.post("/", response_model=RunConfigResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new run configuration",
             description="Create a reusable configuration for test execution with variables, tags, and timeout.")
async def create_run_config(
    config: RunConfigCreate,
    db: Session = Depends(get_db)
) -> RunConfigResponse:
    """
    Create a new run configuration.
    
    Args:
        config: Configuration creation data
        db: Database session
        
    Returns:
        RunConfigResponse: Created configuration
    """
    db_config = crud_run_config.create_run_config(db, config)
    return db_config


# PUBLIC_INTERFACE
@router.get("/", response_model=List[RunConfigResponse],
            summary="List all run configurations",
            description="Retrieve a paginated list of all run configurations.")
async def list_run_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[RunConfigResponse]:
    """
    List all run configurations.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List[RunConfigResponse]: List of configurations
    """
    configs = crud_run_config.get_run_configs(db, skip=skip, limit=limit)
    return configs


# PUBLIC_INTERFACE
@router.get("/{config_id}", response_model=RunConfigResponse,
            summary="Get run configuration details",
            description="Retrieve detailed information about a specific run configuration.")
async def get_run_config(
    config_id: int,
    db: Session = Depends(get_db)
) -> RunConfigResponse:
    """
    Get run configuration by ID.
    
    Args:
        config_id: Configuration ID
        db: Database session
        
    Returns:
        RunConfigResponse: Configuration details
        
    Raises:
        HTTPException: If configuration not found
    """
    db_config = crud_run_config.get_run_config(db, config_id)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run configuration not found"
        )
    return db_config


# PUBLIC_INTERFACE
@router.put("/{config_id}", response_model=RunConfigResponse,
            summary="Update run configuration",
            description="Update an existing run configuration.")
async def update_run_config(
    config_id: int,
    config_update: RunConfigUpdate,
    db: Session = Depends(get_db)
) -> RunConfigResponse:
    """
    Update run configuration.
    
    Args:
        config_id: Configuration ID
        config_update: Update data
        db: Database session
        
    Returns:
        RunConfigResponse: Updated configuration
        
    Raises:
        HTTPException: If configuration not found
    """
    db_config = crud_run_config.update_run_config(db, config_id, config_update)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run configuration not found"
        )
    return db_config


# PUBLIC_INTERFACE
@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete run configuration",
               description="Delete a run configuration.")
async def delete_run_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete run configuration.
    
    Args:
        config_id: Configuration ID
        db: Database session
        
    Raises:
        HTTPException: If configuration not found
    """
    success = crud_run_config.delete_run_config(db, config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run configuration not found"
        )
    return None
