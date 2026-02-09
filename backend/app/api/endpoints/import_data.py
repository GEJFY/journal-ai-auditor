"""Data import API endpoints."""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.import_service import ColumnMapping, ImportService

router = APIRouter()

# Temporary upload directory
UPLOAD_DIR = Path(tempfile.gettempdir()) / "jaia_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class FilePreviewResponse(BaseModel):
    """Response for file preview."""

    filename: str
    total_rows: int
    columns: list[str]
    column_count: int
    suggested_mapping: dict[str, str]
    unmapped_columns: list[str]
    missing_required: list[str]
    sample_data: list[dict[str, Any]]
    dtypes: dict[str, str]


class ValidationResponse(BaseModel):
    """Response for file validation."""

    is_valid: bool
    total_rows: int
    error_count: int
    warning_count: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    check_results: dict[str, Any]


class ImportExecuteRequest(BaseModel):
    """Request to execute data import."""

    temp_file_id: str
    column_mapping: dict[str, str]
    skip_errors: bool = False
    business_unit_code: str = "DEFAULT"
    fiscal_year: int | None = None


class ImportExecuteResponse(BaseModel):
    """Response for import execution."""

    success: bool
    import_id: str
    filename: str
    total_rows: int
    imported_rows: int
    error_rows: int
    warning_rows: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


class MasterImportRequest(BaseModel):
    """Request to import master data."""

    temp_file_id: str
    master_type: Literal["accounts", "departments", "vendors", "users"]


@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
) -> dict:
    """Upload a file for import.

    Stores the file temporarily and returns an ID for subsequent operations.

    Args:
        file: Uploaded file.

    Returns:
        Temporary file ID and filename.
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: .csv, .xlsx, .xls",
        )

    # Generate temp file ID
    import uuid
    temp_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{temp_id}{suffix}"

    # Save file
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return {
        "temp_file_id": temp_id,
        "filename": file.filename,
        "file_type": suffix[1:],
        "file_path": str(temp_path),
    }


@router.get("/preview/{temp_file_id}", response_model=FilePreviewResponse)
async def preview_file(temp_file_id: str) -> FilePreviewResponse:
    """Preview an uploaded file.

    Args:
        temp_file_id: Temporary file ID from upload.

    Returns:
        File preview with columns and sample data.
    """
    # Find the temp file
    temp_files = list(UPLOAD_DIR.glob(f"{temp_file_id}.*"))
    if not temp_files:
        raise HTTPException(status_code=404, detail="File not found")

    temp_path = temp_files[0]

    try:
        service = ImportService()
        preview = service.preview_file(temp_path)
        return FilePreviewResponse(**preview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {e}")


@router.post("/validate/{temp_file_id}", response_model=ValidationResponse)
async def validate_file(
    temp_file_id: str,
    column_mapping: dict[str, str] | None = None,
) -> ValidationResponse:
    """Validate an uploaded file.

    Args:
        temp_file_id: Temporary file ID from upload.
        column_mapping: Optional column mapping.

    Returns:
        Validation results with errors and warnings.
    """
    temp_files = list(UPLOAD_DIR.glob(f"{temp_file_id}.*"))
    if not temp_files:
        raise HTTPException(status_code=404, detail="File not found")

    temp_path = temp_files[0]

    try:
        service = ImportService()
        result = service.validate_file(temp_path, column_mapping)

        return ValidationResponse(
            is_valid=result.is_valid,
            total_rows=result.total_rows,
            error_count=result.error_count,
            warning_count=result.warning_count,
            errors=result.errors[:100],
            warnings=result.warnings[:100],
            check_results=result.check_results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.post("/execute", response_model=ImportExecuteResponse)
async def execute_import(request: ImportExecuteRequest) -> ImportExecuteResponse:
    """Execute data import.

    Args:
        request: Import configuration.

    Returns:
        Import result with statistics.
    """
    temp_files = list(UPLOAD_DIR.glob(f"{request.temp_file_id}.*"))
    if not temp_files:
        raise HTTPException(status_code=404, detail="File not found")

    temp_path = temp_files[0]

    try:
        service = ImportService()
        result = service.import_file(
            file_path=temp_path,
            column_mapping=request.column_mapping,
            skip_errors=request.skip_errors,
            business_unit_code=request.business_unit_code,
            fiscal_year=request.fiscal_year,
        )

        # Clean up temp file on success
        if result.success:
            temp_path.unlink(missing_ok=True)

        return ImportExecuteResponse(
            success=result.success,
            import_id=result.import_id,
            filename=result.filename,
            total_rows=result.total_rows,
            imported_rows=result.imported_rows,
            error_rows=result.error_rows,
            warning_rows=result.warning_rows,
            errors=result.errors,
            warnings=result.warnings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")


@router.post("/master", response_model=ImportExecuteResponse)
async def import_master_data(request: MasterImportRequest) -> ImportExecuteResponse:
    """Import master data (accounts, departments, vendors, users).

    Args:
        request: Master import configuration.

    Returns:
        Import result.
    """
    temp_files = list(UPLOAD_DIR.glob(f"{request.temp_file_id}.*"))
    if not temp_files:
        raise HTTPException(status_code=404, detail="File not found")

    temp_path = temp_files[0]

    try:
        service = ImportService()
        result = service.import_master_data(temp_path, request.master_type)

        # Clean up temp file on success
        if result.success:
            temp_path.unlink(missing_ok=True)

        return ImportExecuteResponse(
            success=result.success,
            import_id=result.import_id,
            filename=result.filename,
            total_rows=result.total_rows,
            imported_rows=result.imported_rows,
            error_rows=result.error_rows,
            warning_rows=result.warning_rows,
            errors=result.errors,
            warnings=result.warnings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Master import failed: {e}")


@router.get("/mapping/suggest")
async def suggest_mapping(columns: str) -> dict:
    """Suggest column mapping based on column names.

    Args:
        columns: Comma-separated list of column names.

    Returns:
        Suggested mapping.
    """
    column_list = [c.strip() for c in columns.split(",")]
    mapping = ColumnMapping.auto_detect(column_list)

    return {
        "suggested_mapping": mapping,
        "unmapped": [c for c in column_list if c not in mapping.values()],
        "missing_required": [
            c for c in ["journal_id", "effective_date", "gl_account_number", "amount", "debit_credit_indicator"]
            if c not in mapping
        ],
    }


@router.delete("/temp/{temp_file_id}")
async def delete_temp_file(temp_file_id: str) -> dict:
    """Delete a temporary uploaded file.

    Args:
        temp_file_id: Temporary file ID.

    Returns:
        Deletion status.
    """
    temp_files = list(UPLOAD_DIR.glob(f"{temp_file_id}.*"))
    if not temp_files:
        return {"deleted": False, "message": "File not found"}

    for f in temp_files:
        f.unlink(missing_ok=True)

    return {"deleted": True, "message": "File deleted"}
