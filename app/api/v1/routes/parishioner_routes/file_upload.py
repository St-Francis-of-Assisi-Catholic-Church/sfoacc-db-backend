from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO
import csv

from app.core.database import get_db
from app.services.parisioner_file_import import ParishionerImportService

router = APIRouter()

@router.post("/import/parishioners", status_code=status.HTTP_201_CREATED)
async def upload_parishioners_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV or TSV file with parishioner data and import it into the database.
    
    The file should have columns matching the parishioner model fields.
    """
    if not (file.filename.endswith('.csv') or file.filename.endswith('.tsv') or file.filename.endswith('.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, TSV or TXT files are allowed"
        )
    
    content = await file.read()
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
            error_bad_lines=False,  # Skip bad lines
            warn_bad_lines=True     # Warn about bad lines
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Validate required columns
    required_columns = ["Last Name (Surname)", "First Name"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}"
        )
    
    # Process the CSV data
    import_service = ParishionerImportService(db)
    result = import_service.import_csv(df)
    
    # Return the import results
    return {
        "message": "Import completed",
        "total_records": result["total"],
        "success_count": result["success"],
        "failed_count": result["failed"],
        "errors": result["errors"][:10]  # Limit errors to first 10
    }

@router.get("/import/template", status_code=status.HTTP_200_OK)
async def get_import_template():
    """
    Get information about the expected file format for parishioner import.
    """
    return {
        "required_columns": [
            "Last Name (Surname)", 
            "First Name"
        ],
        "supported_columns": [
            "Last Name (Surname)",
            "First Name",
            "Other Names",
            "Maiden Name",
            "Gender",
            "Date of Birth",
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
            "Unique ID"
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