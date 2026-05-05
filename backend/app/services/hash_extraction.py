import os
import subprocess
import tempfile
from fastapi import HTTPException
from app.config import SUPPORTED_FORMATS


def _extractor_command(format_config: dict, file_path: str) -> list[str]:
    extractor_path = format_config["extractor_path"]
    if format_config.get("extractor_runtime") == "perl":
        return ["perl", extractor_path, file_path]
    if format_config.get("extractor_runtime") == "python":
        return ["python3", extractor_path, file_path]
    return [extractor_path, file_path]


def _find_hash_line(output: str, markers: list[str]) -> str | None:
    for line in output.splitlines():
        stripped = line.strip()
        if any(marker in stripped for marker in markers):
            return stripped
    return None


def _strip_source_name(hash_string: str, markers: list[str]) -> str:
    marker_positions = [hash_string.find(marker) for marker in markers if marker in hash_string]
    if not marker_positions:
        return hash_string

    stripped = hash_string[min(marker_positions):]
    closers = {
        "$pkzip$": "$/pkzip$",
        "$zip2$": "$/zip2$",
    }
    for marker, closer in closers.items():
        if stripped.startswith(marker) and closer in stripped:
            return stripped[:stripped.index(closer) + len(closer)]

    return stripped


def extract_file_hash(file_path: str, file_type: str, include_source_name: bool = True) -> str:
    """
    Invokes the configured *2john extractor for a supported file type
    and saves it to a new temporary file.

    Args:
        file_path: The path to the temporary uploaded file.
        file_type: Supported file type key, e.g. "pdf" or "zip".
        include_source_name: Keep the "filename:" prefix that John accepts. Hashcat
            usually expects only the hash marker portion.

    Returns:
        The path to the temporary file containing the hash.

    Raises:
        HTTPException: If the hash extraction process fails for any reason.
    """
    format_config = SUPPORTED_FORMATS.get(file_type)
    if not format_config:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{file_type}'.")

    extractor_path = format_config["extractor_path"]
    if not os.path.isfile(extractor_path):
        raise HTTPException(
            status_code=501,
            detail=(
                f"Server dependency missing: extractor for '{file_type}' was not found at '{extractor_path}'. "
                "Install John the Ripper jumbo or set the corresponding environment variable."
            )
        )

    command = _extractor_command(format_config, file_path)
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
            detail=f"Server dependency missing: Could not find '{command[0]}'. Please check server configuration."
        )
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process file. It may not be password-protected or it could be corrupt. Tool output: '{error_output}'"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408, # 408 Request Timeout
            detail="Hash extraction timed out. The file may be too complex or large."
        )

    markers = format_config["hash_markers"]
    hash_string = _find_hash_line(process.stdout, markers)

    if not hash_string:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract a valid hash from the {file_type.upper()} file. Please ensure it is password-protected."
        )

    if not include_source_name:
        hash_string = _strip_source_name(hash_string, markers)

    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix="_hash.txt", prefix=f"{file_type}_") as hash_file:
            hash_file.write(hash_string + "\n")
            return hash_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save extracted hash to a temporary file: {e}")


def extract_pdf_hash(pdf_path: str, include_source_name: bool = True) -> str:
    return extract_file_hash(pdf_path, "pdf", include_source_name)
