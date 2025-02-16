from typing import Optional, List

import logging
from fastapi import FastAPI, APIRouter, HTTPException  # Import HTTPException
from pydantic import BaseModel  # For JSON input validation
from haystack.document_stores import BaseDocumentStore
from haystack.schema import Document

from utils import get_app, get_pipelines
from rest_api.config import LOG_LEVEL
from schema import FilterRequest

# Add imports from your previous code
import sqlite3
from envs import FAQ_TYPE_2_LECTURER_DATA_URL
from type_2_helpers import conn  # Assuming this is in the same module or adjust import accordingly

logging.getLogger("haystack").setLevel(LOG_LEVEL)
logger = logging.getLogger("haystack")

router = APIRouter()
app: FastAPI = get_app()

# Define a Pydantic model for the incoming JSON data
class LecturerData(BaseModel):
    id: str
    last_middle_name: str
    first_name: str
    department: str
    academic_title: str
    rank: str
    kiem_nghiem: str
    bc: str
    hd_t: str

@router.post(
    "/type2/update_cbnv_database"
)
def update_cbnv_database(data: List[LecturerData]):
    """
    This endpoint clears all data from the lecturers_data table (without dropping it)
    and inserts new data provided in the JSON input.

    Example input:
    [
        {
            "id": "003778",
            "last_middle_name": "Trần Tuấn",
            "first_name": "Anh",
            "department": "BỘ MÔN KHOA HỌC MÁY TÍNH (DEPARTMENT OF COMPUTER SCIENCE)",
            "academic_title": "TS",
            "rank": "GV",
            "kiem_nghiem": "",
            "bc": "1",
            "hd_t": ""
        }
    ]
    """
    try:
        cursor = conn.cursor()

        # Clear all data from the lecturers_data table
        cursor.execute("DELETE FROM lecturers_data")
        conn.commit()
        logger.info("Cleared all data from lecturers_data table")

        # Prepare the insert query based on the table structure
        insert_query = """
        INSERT INTO lecturers_data (
            "MSCB", "Họ và tên đệm", "Tên", "Bộ môn", "Học hàm/học vị", 
            "Ngạch", "Kiêm nhiệm", "BC", "HĐ T"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Map the JSON data to the table columns and insert
        for lecturer in data:
            cursor.execute(insert_query, (
                lecturer.id,                    # MSCB
                lecturer.last_middle_name,      # Họ và tên đệm
                lecturer.first_name,            # Tên
                lecturer.department,            # Bộ môn
                lecturer.academic_title,        # Học hàm/học vị
                lecturer.rank,                  # Ngạch
                lecturer.kiem_nghiem,           # Kiêm nghiệm
                lecturer.bc,                    # BC
                lecturer.hd_t                   # HĐ T
            ))

        conn.commit()
        logger.info(f"Inserted {len(data)} records into lecturers_data table")

        return {"response": "update success"}

    except Exception as e:
        logger.error(f"Error updating lecturers_data table: {str(e)}")
        # Raise an HTTPException with a 500 status code (or another appropriate code)
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail={"response": "update failed", "error": str(e)}
        )