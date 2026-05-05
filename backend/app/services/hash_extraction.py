import os
import subprocess
import tempfile
from fastapi import HTTPException
from app.config import PDF2JOHN_PATH

def extract_pdf_hash(pdf_path: str, include_source_name: bool = True) -> str:
    """
    Invokes pdf2john.pl to extract the hash string from a PDF file
    and saves it to a new temporary file.

    Args:
        pdf_path: The path to the temporary PDF file.
        include_source_name: Keep the "filename:" prefix that John accepts. Hashcat
            expects only the "$pdf$..." portion.

    Returns:
        The path to the temporary file containing the hash.

    Raises:
        HTTPException: If the hash extraction process fails for any reason.
    """
    if not os.path.isfile(PDF2JOHN_PATH):
        raise HTTPException(
            status_code=501,
            detail=(
                f"Server dependency missing: pdf2john was not found at '{PDF2JOHN_PATH}'. "
                "Install John the Ripper jumbo or set PDF2JOHN_PATH to the correct pdf2john path."
            )
        )

    command = ['perl', PDF2JOHN_PATH, pdf_path]
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # Raises CalledProcessError on non-zero exit codes
            timeout=30   # Prevent the process from hanging indefinitely
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=501, # 501 Not Implemented, as a server dependency is missing
            detail=f"Server dependency missing: Could not find '{command[0]}' or '{command[1]}'. Please check server configuration."
        )
    except subprocess.CalledProcessError as e:
        # This typically occurs if the file is not a valid PDF or not encrypted.
        error_output = e.stderr.strip() or e.stdout.strip()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process PDF. It may not be password-protected or it could be corrupt. Tool output: '{error_output}'"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408, # 408 Request Timeout
            detail="Hash extraction timed out. The PDF may be too complex or large."
        )

    hash_lines = [line.strip() for line in process.stdout.splitlines() if "$pdf$" in line]

    # pdf2john.pl commonly outputs "filename:$pdf$..." instead of only "$pdf$...".
    if not hash_lines:
        raise HTTPException(status_code=400, detail="Could not extract a valid hash from the PDF. Please ensure it is password-protected.")

    hash_string = hash_lines[0]
    if not include_source_name and "$pdf$" in hash_string:
        hash_string = hash_string[hash_string.index("$pdf$"):]

    # Save the extracted hash to its own temporary file for the next stage.
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix="_hash.txt", prefix="pdf_") as hash_file:
            hash_file.write(hash_string + "\n")
            return hash_file.name
    except Exception as e:
        # Handle potential I/O errors when writing the hash file
        raise HTTPException(status_code=500, detail=f"Failed to save extracted hash to a temporary file: {e}")
