from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import uuid
from pathlib import Path
from typing import Annotated

from app.services.secure_upload import save_temporary_pdf
from app.services.hash_extraction import extract_pdf_hash
from app.services.cracking_orchestrator import start_cracking_task, jobs

app = FastAPI(title="PDF Cracker Service")
STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

@app.get("/")
def read_root():
    return {"message": "PDF Cracker API is running."}

@app.post("/api/v1/crack/pdf", status_code=202)
async def crack_pdf(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF file to crack.")],
    engine: Annotated[str, Form(description="Cracking engine: 'john' or 'hashcat'.")],
    wordlist_id: Annotated[str, Form(description="Wordlist to use, e.g., 'rockyou'.")] = "",
    hashcat_mode: Annotated[int | None, Form(description="Required if engine is 'hashcat'.")] = None,
    hashcat_attack: Annotated[str, Form(description="Hashcat attack: 'wordlist' or 'bruteforce'.")] = "wordlist",
    hashcat_mask: Annotated[str | None, Form(description="Required for Hashcat brute force, e.g., '?d?d?d?d?d?d'.")] = None,
):
    """
    Accepts a cracking job, starts it in the background, and returns a job ID.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are accepted.")
    if engine == "hashcat" and hashcat_mode is None:
        raise HTTPException(status_code=400, detail="Hashcat mode is required when using the 'hashcat' engine.")
    if engine == "hashcat" and hashcat_attack == "bruteforce" and not hashcat_mask:
        raise HTTPException(status_code=400, detail="Hashcat mask is required when using brute force.")

    temp_pdf_path = None
    temp_hash_path = None

    try:
        temp_pdf_path = save_temporary_pdf(file)
        temp_hash_path = extract_pdf_hash(temp_pdf_path, include_source_name=engine == "john")
    except Exception as e:
        # If setup fails, cleanup and re-raise
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise e
    finally:
        # The original PDF is always cleaned up after hash extraction
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "result": None}

    background_tasks.add_task(
        start_cracking_task,
        job_id,
        engine,
        temp_hash_path,
        wordlist_id,
        hashcat_mode,
        hashcat_attack,
        hashcat_mask,
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Attack initiated in background."
    }

@app.get("/api/v1/crack/status/{job_id}")
def get_job_status(job_id: str):
    """Retrieves the status and result of a cracking job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {"status": job["status"]}
    if "attack" in job:
        response["attack"] = job["attack"]
    if job["status"] in ["cracked", "not_cracked", "failed"]:
        response["result"] = job["result"]
        # Optional: remove job from memory after it's fetched and completed
        # del jobs[job_id]
    
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["app"])
