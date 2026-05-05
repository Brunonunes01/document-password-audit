import tempfile
import shutil
from fastapi import UploadFile

def save_temporary_pdf(file: UploadFile) -> str:
    """
    Saves the uploaded PDF to a secure, temporary file on disk.

    Args:
        file: The uploaded file from the FastAPI request.

    Returns:
        The absolute path to the temporary file.
    """
    try:
        # Create a temporary file with a .pdf suffix.
        # 'delete=False' is crucial because we need the file to persist
        # after this context manager closes. We are responsible for its cleanup.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="pdf_cracker_") as tmp_file:
            # Stream the uploaded file content to the temporary file.
            # This is memory-efficient as it avoids loading the whole file into memory.
            shutil.copyfileobj(file.file, tmp_file)
            return tmp_file.name
    finally:
        # Ensure the uploaded file stream is closed.
        file.file.close()
