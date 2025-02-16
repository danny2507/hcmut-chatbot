import csv
import io
import sqlite3

import requests

from envs import FAQ_TYPE_2_LECTURER_DATA_URL


class Type2QueryMaker:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def how_many_lecturers_is_title(self, title):
        cursor = self.db_connection.cursor()
        query = """
        SELECT COUNT(*) 
        FROM lecturers_data 
        WHERE "Học hàm/học vị" = ?
        """
        cursor.execute(query, (title,))
        result = cursor.fetchone()
        return f"Số giảng viên có học vị {title}: {result[0]}"

    def how_many_lecturers_is_title_and_above(self, title):
        cursor = self.db_connection.cursor()

        hierarchy = {
            "GS": 5,
            "PGS": 4,
            "TS": 3,
            "ThS": 2,
            "KS": 1,
            "CN": 0
        }

        min_rank = hierarchy[title]
        valid_titles = [t for t, rank in hierarchy.items() if rank >= min_rank]

        query = f"""
        SELECT COUNT(*)
        FROM lecturers_data
        WHERE "Học hàm/học vị" IN ({', '.join(['?'] * len(valid_titles))})
        """
        cursor.execute(query, valid_titles)
        result = cursor.fetchone()
        return (f"Số giảng viên có học vị {title} trở lên: {result[0]}")
    def how_many_lecturers_is_rank(self, rank):
        cursor = self.db_connection.cursor()
        query = """
        SELECT COUNT(*) 
        FROM lecturers_data 
        WHERE "Ngạch" = ?
        """
        cursor.execute(query, (rank,))
        result = cursor.fetchone()
        return f"Số giảng viên có ngạch {rank}: {result[0]}"

    def list_lecturers_in_department(self, department):
        cursor = self.db_connection.cursor()
        query = """
           SELECT "Học hàm/học vị", COUNT(*)
           FROM lecturers_data
           WHERE "Bộ môn" = ?
           GROUP BY "Học hàm/học vị"
           """
        cursor.execute(query, (department,))
        results = cursor.fetchall()

        title_map = {
            "TS": "tiến sĩ",
            "ThS": "thạc sĩ",
            "CN": "cử nhân",
            "PGS": "phó giáo sư",
            "GS": "giáo sư",
            "KS": "kỹ sư"
        }

        details = [f"{count} {title_map.get(title, title)}" for title, count in results]
        details_str = ", ".join(details)

        return f"Bộ môn {department} có {details_str}"

def create_sqlite_db_from_csv(csv_url):
    """
    Downloads a CSV file from a URL, creates an in-memory SQLite database,
    and populates a table named "lecturers_data" with the CSV data.

    Args:
        csv_url: The URL of the CSV file.
    """

    try:
        response = requests.get(csv_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        csv_text = response.content.decode('utf-8')
    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV: {e}")
        return

    # Read CSV data using the io.StringIO buffer
    csv_file = io.StringIO(csv_text)
    csv_reader = csv.reader(csv_file)

    # Get header row
    header = next(csv_reader)

    # Connect to an in-memory SQLite database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create table with column names from the header
    columns_text = ", ".join(f'"{col}" TEXT' for col in header)
    create_table_sql = f"CREATE TABLE lecturers_data ({columns_text})"
    cursor.execute(create_table_sql)

    # Insert data into the table
    insert_sql = f"INSERT INTO lecturers_data VALUES ({', '.join(['?'] * len(header))})"
    for row in csv_reader:
        cursor.execute(insert_sql, row)

    conn.commit()
    print("Sucessfully created SQLite database for type 2 querying.")

    return conn

conn = create_sqlite_db_from_csv(FAQ_TYPE_2_LECTURER_DATA_URL)
query_maker = Type2QueryMaker(conn)


function_map = {
    "how_many_lecturers_is_title": query_maker.how_many_lecturers_is_title,
    "how_many_lecturers_is_title_and_above": query_maker.how_many_lecturers_is_title_and_above,
    "how_many_lecturers_is_rank": query_maker.how_many_lecturers_is_rank,
    "list_lecturers_in_department": query_maker.list_lecturers_in_department,
}
def execute_type_2_query(func_name, param):

    func = function_map.get(func_name)
    if func:
        return func(param)
    else:
        print("Function not found.")