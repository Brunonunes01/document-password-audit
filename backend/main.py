from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import uuid
from pathlib import Path
from typing import Annotated

from app.config import SUPPORTED_FORMATS
from app.services.secure_upload import save_temporary_file
from app.services.hash_extraction import extract_file_hash
from app.services.cracking_orchestrator import start_cracking_task, jobs

app = FastAPI(title="Document Password Audit Service")
STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

@app.get("/")
def read_root():
    return {
        "message": "Document Password Audit API is running.",
        "supported_formats": list(SUPPORTED_FORMATS.keys()),
    }

async def _create_cracking_job(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    file_type: str,
    engine: str,
    wordlist_id: str,
    hashcat_mode: int | None,
    hashcat_attack: str,
    hashcat_mask: str | None,
    hashcat_charset: str,
    hashcat_min_length: int | None,
    hashcat_max_length: int | None,
):
    format_config = SUPPORTED_FORMATS.get(file_type)
    if not format_config:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{file_type}'.")

    if engine not in ["john", "hashcat"]:
        raise HTTPException(status_code=400, detail="Invalid cracking engine specified.")

    if hashcat_attack not in ["wordlist", "bruteforce", "bruteforce_range"]:
        raise HTTPException(status_code=400, detail="Invalid Hashcat attack. Use 'wordlist', 'bruteforce', or 'bruteforce_range'.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name.")

    filename = file.filename.lower()
    extensions = format_config["extensions"]
    if not any(filename.endswith(extension) for extension in extensions):
        allowed = ", ".join(extensions)
        raise HTTPException(status_code=400, detail=f"Invalid file type. Expected: {allowed}.")

    if engine == "hashcat" and hashcat_mode is None:
        hashcat_mode = format_config.get("default_hashcat_mode")
    if engine == "hashcat" and hashcat_mode is None:
        raise HTTPException(status_code=400, detail="Hashcat mode is required when using the 'hashcat' engine.")
    if engine == "hashcat" and hashcat_attack == "bruteforce" and not hashcat_mask:
        raise HTTPException(status_code=400, detail="Hashcat mask is required when using brute force.")
    if engine == "hashcat" and hashcat_attack == "bruteforce_range":
        if hashcat_charset not in ["?d"]:
            raise HTTPException(status_code=400, detail="Only numeric charset '?d' is currently supported for brute force range.")
        if hashcat_min_length is None or hashcat_max_length is None:
            raise HTTPException(status_code=400, detail="Minimum and maximum lengths are required for brute force range.")
        if hashcat_min_length < 1 or hashcat_max_length < hashcat_min_length or hashcat_max_length > 12:
            raise HTTPException(status_code=400, detail="Invalid brute force range. Use minimum >= 1, maximum >= minimum, and maximum <= 12.")

    temp_file_path = None
    temp_hash_path = None

    try:
        temp_file_path = save_temporary_file(file, extensions[0])
        temp_hash_path = extract_file_hash(temp_file_path, file_type, include_source_name=engine == "john")
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise e
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "result": None, "file_type": file_type}

    background_tasks.add_task(
        start_cracking_task,
        job_id,
        engine,
        temp_hash_path,
        wordlist_id,
        hashcat_mode,
        hashcat_attack,
        hashcat_mask,
        file_type,
        hashcat_charset,
        hashcat_min_length,
        hashcat_max_length,
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Attack initiated in background."
    }

@app.post("/api/v1/crack/file", status_code=202)
async def crack_file(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="File to audit.")],
    file_type: Annotated[str, Form(description="File type: 'pdf' or 'zip'.")],
    engine: Annotated[str, Form(description="Cracking engine: 'john' or 'hashcat'.")],
    wordlist_id: Annotated[str, Form(description="Wordlist to use, e.g., 'rockyou'.")] = "",
    hashcat_mode: Annotated[int | None, Form(description="Required if engine is 'hashcat'.")] = None,
    hashcat_attack: Annotated[str, Form(description="Hashcat attack: 'wordlist', 'bruteforce', or 'bruteforce_range'.")] = "wordlist",
    hashcat_mask: Annotated[str | None, Form(description="Required for Hashcat brute force, e.g., '?d?d?d?d?d?d'.")] = None,
    hashcat_charset: Annotated[str, Form(description="Charset for Hashcat brute force range. Currently supports '?d'.")] = "?d",
    hashcat_min_length: Annotated[int | None, Form(description="Minimum length for brute force range.")] = None,
    hashcat_max_length: Annotated[int | None, Form(description="Maximum length for brute force range.")] = None,
):
    """Accepts a supported file, starts cracking in the background, and returns a job ID."""
    return await _create_cracking_job(
        background_tasks,
        file,
        file_type,
        engine,
        wordlist_id,
        hashcat_mode,
        hashcat_attack,
        hashcat_mask,
        hashcat_charset,
        hashcat_min_length,
        hashcat_max_length,
    )

@app.post("/api/v1/crack/pdf", status_code=202)
async def crack_pdf(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF file to crack.")],
    engine: Annotated[str, Form(description="Cracking engine: 'john' or 'hashcat'.")],
    wordlist_id: Annotated[str, Form(description="Wordlist to use, e.g., 'rockyou'.")] = "",
    hashcat_mode: Annotated[int | None, Form(description="Required if engine is 'hashcat'.")] = None,
    hashcat_attack: Annotated[str, Form(description="Hashcat attack: 'wordlist', 'bruteforce', or 'bruteforce_range'.")] = "wordlist",
    hashcat_mask: Annotated[str | None, Form(description="Required for Hashcat brute force, e.g., '?d?d?d?d?d?d'.")] = None,
    hashcat_charset: Annotated[str, Form(description="Charset for Hashcat brute force range. Currently supports '?d'.")] = "?d",
    hashcat_min_length: Annotated[int | None, Form(description="Minimum length for brute force range.")] = None,
    hashcat_max_length: Annotated[int | None, Form(description="Maximum length for brute force range.")] = None,
):
    """Backward-compatible PDF endpoint."""
    return await _create_cracking_job(
        background_tasks,
        file,
        "pdf",
        engine,
        wordlist_id,
        hashcat_mode,
        hashcat_attack,
        hashcat_mask,
        hashcat_charset,
        hashcat_min_length,
        hashcat_max_length,
    )

@app.get("/api/v1/crack/status/{job_id}")
def get_job_status(job_id: str):
    """Retrieves the status and result of a cracking job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {"status": job["status"]}
    if "file_type" in job:
        response["file_type"] = job["file_type"]
    if "attack" in job:
        response["attack"] = job["attack"]
    if job["status"] in ["cracked", "not_cracked", "failed"]:
        response["result"] = job["result"]
        # Optional: remove job from memory after it's fetched and completed
        # del jobs[job_id]
    
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["app"])
