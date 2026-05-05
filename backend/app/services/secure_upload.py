import tempfile
import shutil
from fastapi import UploadFile

def save_temporary_file(file: UploadFile, suffix: str) -> str:
    """
    Saves the uploaded file to a secure, temporary file on disk.

    Args:
        file: The uploaded file from the FastAPI request.
        suffix: Extension to use for the temporary file.

    Returns:
        The absolute path to the temporary file.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="password_audit_") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            return tmp_file.name
    finally:
        file.file.close()


def save_temporary_pdf(file: UploadFile) -> str:
    return save_temporary_file(file, ".pdf")
