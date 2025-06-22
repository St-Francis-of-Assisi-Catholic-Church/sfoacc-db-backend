from datetime import datetime
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO, BytesIO
import csv
import re
from typing import List, Dict, Any, Optional

from app.api.deps import SessionDep, CurrentUser
from app.models.user import UserRole
from app.services.parishioner_file_import import ParishionerImportService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file_upload_router = APIRouter()

def is_valid_email(email: str) -> bool:
    """
    Validate email address using regex pattern.
    
    Args:
        email: Email string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not email or pd.isna(email):
        return True  # Empty email is allowed
    
    email = str(email).strip()
    
    # If email is empty after stripping, it's valid (optional field)
    if not email:
        return True
    
    # Email regex pattern - comprehensive but not overly strict
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return re.match(email_pattern, email) is not None

def sanitize_email(email: str) -> Optional[str]:
    """
    Sanitize email address - convert to lowercase and strip whitespace.
    
    Args:
        email: Email string to sanitize
        
    Returns:
        str or None: Sanitized email or None if empty
    """
    if pd.isna(email) or not email:
        return None
    
    email = str(email).strip().lower()
    
    # Return None for empty strings after stripping
    if not email:
        return None
    
    return email

def is_valid_date_format(date_str: str) -> bool:
    """
    Check if date string is in a valid format (YYYY-MM-DD or DD/MM/YYYY)
    
    Args:
        date_str: Date string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Remove any whitespace
    date_str = date_str.strip()
    
    # Check for ISO format (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    # Check for DD/MM/YYYY format
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            datetime.strptime(date_str, '%d/%m/%Y')
            return True
        except ValueError:
            return False
    
    return False

def convert_date_format(date_str: str) -> Optional[str]:
    """
    Convert date string to ISO format (YYYY-MM-DD) or return None for empty/invalid dates
    
    Args:
        date_str: Date string to convert
        
    Returns:
        str or None: Date in ISO format (YYYY-MM-DD) or None
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Return None for empty strings after stripping
    if not date_str:
        return None
    
    # Already in ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Convert from DD/MM/YYYY to YYYY-MM-DD
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return date_str
    
    return date_str

def validate_csv_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate the CSV data before importing.
    
    Returns:
        Dict with 'valid' flag and errors list if any
    """
    errors = []
    
    # Check required columns - Date of Birth is no longer required
    required_columns = ["Last Name (Surname)", "First Name", "Gender"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            "valid": False,
            "errors": [f"Missing required columns: {', '.join(missing_columns)}"]
        }
    
    # Validate data in rows
    for idx, row in df.iterrows():
        row_errors = []
        
        # Skip completely empty rows
        if row.isna().all():
            continue
            
        # Check required fields exist in each row
        for col in required_columns:
            if pd.isna(row[col]) or not str(row[col]).strip():
                row_errors.append(f"Missing value for required field: {col}")
        
        # Validate Date of Birth (optional but must be valid format if provided)
        if "Date of Birth" in df.columns and not pd.isna(row["Date of Birth"]):
            dob = str(row["Date of Birth"]).strip()
            
            # Check for N/A values and flag as error
            if dob.lower() in ["n/a", "na"]:
                row_errors.append(f"Date of Birth contains 'N/A'. Please update and try again")
            elif dob and not is_valid_date_format(dob):
                row_errors.append(f"Invalid date format for Date of Birth: {dob}. Expected format: YYYY-MM-DD or DD/MM/YYYY")
        
        # Validate gender
        if not pd.isna(row["Gender"]):
            gender = str(row["Gender"]).strip().lower()
            if gender not in ["male", "female", "m", "f"]:
                row_errors.append(f"Invalid gender: {row['Gender']}. Expected: Male or Female")
        
        # Validate email address if present
        if "Email Address" in df.columns and not pd.isna(row["Email Address"]):
            email = str(row["Email Address"]).strip()
            if email and not is_valid_email(email):
                row_errors.append(f"Invalid email format: {email}")
        
        # Add other validations as needed
        
        if row_errors:
            errors.append(f"Row {idx+2} (Line {idx+2} in file): {'; '.join(row_errors)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def standardize_list_items(text_list):
    """
    Standardize a list of items into semicolon-separated format.
    Handles multiple delimiters: commas, semicolons, 'and', etc.
    
    Args:
        text_list: A string containing list items with various delimiters
    
    Returns:
        A string with items separated by semicolons
    """
    if pd.isna(text_list) or not text_list:
        return ""
    
    text = str(text_list).strip()
    
    # Replace common delimiters with a placeholder
    text = text.replace(', and ', '|||')
    text = text.replace(' and ', '|||')
    text = text.replace(',', '|||')
    text = text.replace(';', '|||')
    
    # Split by the placeholder
    items = [item.strip() for item in text.split('|||')]
    
    # Filter out empty items and join with semicolons
    return ';'.join([item for item in items if item])

def preprocess_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess CSV data before importing:
    - Convert names to sentence case
    - Standardize delimiters
    - Clean data
    - Sanitize emails
    - Handle dates
    """
    # Convert text columns to sentence case
    text_columns = [
        "Last Name (Surname)", "First Name", "Other Names", "Maiden Name",
        "Hometown", "Region/State", "Country", "Current place of Residence/Area"
    ]
    
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).strip().title() if not pd.isna(x) and str(x).strip() else None
            )
    
    # Standardize multi-value fields to use semicolons
    multi_value_columns = [
        "Church Sacrements", 
        "Name of Kids (if any)", 
        "Skills/Talents", 
        "Languages Spoken", 
        "Church Groups/Societies",
        "Medical Conditions"
    ]

    for col in multi_value_columns:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: standardize_list_items(x) if not pd.isna(x) else None
            )

    # Convert date formats to ISO format or None
    if "Date of Birth" in df.columns:
        df["Date of Birth"] = df["Date of Birth"].apply(
            lambda x: convert_date_format(str(x)) if not pd.isna(x) and str(x).strip() else None
        )
    
    # Sanitize email addresses
    if "Email Address" in df.columns:
        df["Email Address"] = df["Email Address"].apply(
            lambda x: sanitize_email(str(x)) if not pd.isna(x) else None
        )
    
    return df

@file_upload_router.post("/batch", status_code=status.HTTP_201_CREATED)
async def upload_parishioners_csv(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    Upload a CSV or TSV file with parishioner data and import it into the database.
    
    The file should have columns matching the parishioner model fields.
    Required columns: "Last Name (Surname)", "First Name", "Gender"
    Optional columns: "Date of Birth", "Email Address", etc.
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Only super admins can import parishioners."
        )
  
    # Validate file type
    if not (file.filename.endswith('.csv') or file.filename.endswith('.tsv') or file.filename.endswith('.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, TSV or TXT files are allowed"
        )
    
    # Read file content
    content = await file.read()
    
    try:
        # Detect the delimiter based on file content
        string_io = StringIO(content.decode('utf-8'))
        sample = string_io.read(1024)
        string_io.seek(0)
        
        # Use csv.Sniffer to detect delimiter if possible
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except csv.Error:
            # Default to comma if detection fails
            delimiter = ','
        
        # Read the CSV with detected or default delimiter
        df = pd.read_csv(
            string_io, 
            delimiter=delimiter,
            engine='python',
            on_bad_lines="warn",
            dtype=str,  # Read all columns as strings to prevent type conversion issues
        )
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Validate the data
        validation_result = validate_csv_data(df)
        if not validation_result["valid"]:
            return {
                "success": False,
                "message": "Validation failed",
                "errors": validation_result["errors"][:20]  # Limit to first 20 errors
            }
        
        # Preprocess the data (convert to sentence case, standardize delimiters, etc.)
        df = preprocess_csv_data(df)
        
        # Process the CSV data using the import service
        import_service = ParishionerImportService(session)
        result = import_service.import_csv(df)
        
        # Return the import results
        return {
            "success": True,
            "message": "Import completed",
            "imported_count": result["success"],
            "total_records": result["total"],
            "success_count": result["success"],
            "failed_count": result["failed"],
            "errors": result["errors"][:20] if result["errors"] else []  # Limit errors to first 20
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {str(e)}"
        )

@file_upload_router.get("/template", status_code=status.HTTP_200_OK)
async def get_import_template():
    """
    Get information about the expected file format for parishioner import.
    """
    return {
        "success": True,
        "message": "Template fetched successfully",
        "template": {
            "required_columns": [
                "Last Name (Surname)", 
                "First Name",
                "Gender"
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
                "Medical Conditions",
                "Church Sacrements",
                "Marital Status",
                "Spouse Name",
                "Name of Kids (if any)",
                "Father's Name",
                "Father's Life Status",
                "Mother's Name",
                "Mother's Life Status",
                "Unique ID ",
                "Place of Worship",
                "Current place of Residence/Area",
                "Languages Spoken",
                "Church Groups/Societies",
                "Church Community"
            ],
            "format_rules": [
                "The file can be CSV or TSV format",
                "Date of Birth is optional. If provided, should be in format YYYY-MM-DD or DD/MM/YYYY (e.g., 1990-05-20 or 20/05/1990)",
                "Do not use 'N/A' or 'n/a' for Date of Birth - leave empty if unknown",
                "Email Address is optional. If provided, must be a valid email format (e.g., user@domain.com)",
                "Gender should be 'Male' or 'Female' (or 'M'/'F')",
                "Multiple items should be separated by semicolons (;) or comma (,)",
                "Names will be converted to sentence case",
                "Email addresses will be converted to lowercase",
                "Required fields: Last Name, First Name, Gender"
            ],
            "example_data": [
                {
                    "Last Name (Surname)": "Smith",
                    "First Name": "John",
                    "Gender": "Male",
                    "Date of Birth": "1985-04-15",
                    "Email Address": "john.smith@email.com",
                    "Church Sacrements": "BAPTISM;FIRST COMMUNION",
                    "Skills/Talents": "Singing;Playing Piano;Teaching"
                }
            ]
        }
    }