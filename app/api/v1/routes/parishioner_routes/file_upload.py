import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO
import csv

from app.api.deps import SessionDep, CurrentUser
from app.core.database import Database as db
from app.models.user import UserRole
from app.services.parisioner_file_import import ParishionerImportService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file_upload_router = APIRouter()

@file_upload_router.post("/parishioners", status_code=status.HTTP_201_CREATED, )
async def upload_parishioners_csv(
    session: SessionDep ,
    current_user: CurrentUser,
    file: UploadFile = File(...),

):
    """
    Upload a CSV or TSV file with parishioner data and import it into the database.
    
    The file should have columns matching the parishioner model fields.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
             status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Only super admins can update users."
        )
  
    if not (file.filename.endswith('.csv') or file.filename.endswith('.tsv') or file.filename.endswith('.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, TSV or TXT files are allowed"
        )
    
    content = await file.read()
    logger.info(content)
    try:
        # Detect the delimiter based on file content
        string_io = StringIO(content.decode('utf-8'))
        dialect = csv.Sniffer().sniff(string_io.read(1024))
        string_io.seek(0)
        
        # Use detected delimiter
        df = pd.read_csv(
            string_io, 
            delimiter=dialect.delimiter,
            engine='python',
            on_bad_lines="warn",  # Warn about bad lines
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Validate required columns
    required_columns = ["Last Name (Surname)", "First Name", "Date of Birth"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}"
        )
    
    # Process the CSV data
    import_service = ParishionerImportService(session)
    result = import_service.import_csv(df)
    
    # Return the import results
    return {
        "message": "Import completed",
        "total_records": result["total"],
        "success_count": result["success"],
        "failed_count": result["failed"],
        "errors": result["errors"][:10]  # Limit errors to first 10
    }

@file_upload_router.get("/template", status_code=status.HTTP_200_OK)
async def get_import_template():
    """
    Get information about the expected file format for parishioner import.
    """
    return {
        "required_columns": [
            "Last Name (Surname)", 
            "First Name",
            "Date of Birth"
        ],
        "supported_columns": [
            "Last Name (Surname)",
            "First Name",
            "Other Names",
            "Maiden Name",
            "Gender",
            "Place of Birth",
            "Hometown",
            "Region/State",
            "Country",
            "Mobile Number",
            "WhatsApp Number",
            "Email Address",
            "Occupation/Profession (Indicate Self-Employed or Not Employed)",
            "Current Workplace / Employer",
            "Skills/Talents",
            "Emergency Contact Name",
            "Emergency Contact Number",
            "Any Medical Condition",
            "If Yes, Please State",
            "Church Sacrements",
            "Marital Status",
            "Spouse Name",
            "Name of Kids (if any)",
            "FATHER'S NAME",
            "Father's Life Status",
            "MOTHER'S NAME",
            "Mother's Life Status",
            "Unique/ Old Church ID",
            "Place of Worship",
            "Current place of Residence/Area"
        ],
        "notes": [
            "The file can be CSV or TSV format",
            "Date of Birth should be in format DD/MM/YYYY",
            "Gender should be 'Male' or 'Female'",
            "Skills/Talents can be comma-separated list",
            "Name of Kids can be comma-separated list",
            "Church Sacrements should be semicolon-separated list of sacraments (e.g., 'Baptism;First Communion')",
            "Father's Life Status and Mother's Life Status should indicate if 'Alive' or 'Deceased'"
        ]
    }