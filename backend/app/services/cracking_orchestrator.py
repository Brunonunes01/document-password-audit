# backend/app/services/cracking_orchestrator.py
import asyncio
import os
from typing import Dict

from app.config import JOHN_PATH, HASHCAT_PATH, WORDLISTS

# In-memory store for job statuses.
# For production, a more persistent store like Redis or a DB would be used.
jobs: Dict[str, Dict] = {}


async def _run_john(job_id: str, hash_path: str, wordlist_path: str):
    """Executes John the Ripper and attempts to find the password."""
    jobs[job_id]["status"] = "cracking_cpu"

    if not (os.path.isfile(JOHN_PATH) and os.access(JOHN_PATH, os.X_OK)):
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = (
            f"John the Ripper was not found or is not executable at '{JOHN_PATH}'. "
            "Install John the Ripper or set JOHN_PATH to the correct executable."
        )
        return
    
    # Command to start the cracking process
    command_run = [JOHN_PATH, f"--wordlist={wordlist_path}", hash_path]
    
    process = await asyncio.create_subprocess_exec(
        *command_run,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        # Check stderr for common JtR messages if the primary run fails
        error_output = stderr.decode().strip()
        if "No password hashes loaded" in error_output:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "No password hash found in the provided file."
            return
        # Generic failure
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = f"John the Ripper failed. Stderr: {error_output}"
        return

    # Command to show the cracked password
    command_show = [JOHN_PATH, "--show", hash_path]
    process_show = await asyncio.create_subprocess_exec(
        *command_show,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout_show, _ = await process_show.communicate()
    
    output = stdout_show.decode().strip()
    # JtR's --show output is typically "source-file:password" followed by a summary.
    for line in output.splitlines():
        if ":" not in line:
            continue

        password = line.split(":", 1)[1].split(" ")[0].strip()
        if password:
            jobs[job_id]["status"] = "cracked"
            jobs[job_id]["result"] = password
            return

    jobs[job_id]["status"] = "not_cracked"
    jobs[job_id]["result"] = "Password not found in the provided wordlist."


async def _run_hashcat(
    job_id: str,
    hash_path: str,
    hashcat_mode: int,
    wordlist_path: str | None = None,
    attack_mode: str = "wordlist",
    mask: str | None = None,
):
    """Executes Hashcat and attempts to find the password."""
    jobs[job_id]["status"] = "cracking_gpu"

    if not (os.path.isfile(HASHCAT_PATH) and os.access(HASHCAT_PATH, os.X_OK)):
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = (
            f"Hashcat was not found or is not executable at '{HASHCAT_PATH}'. "
            "Install Hashcat or set HASHCAT_PATH to the correct executable."
        )
        return

    command = [HASHCAT_PATH, "-m", str(hashcat_mode)]

    if attack_mode == "bruteforce":
        if not mask:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Hashcat mask is required for brute force mode."
            return

        jobs[job_id]["attack"] = f"hashcat brute force ({mask})"
        command.extend(["-a", "3", hash_path, mask])
    else:
        if not wordlist_path:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Wordlist is required for Hashcat wordlist mode."
            return

        jobs[job_id]["attack"] = f"hashcat wordlist ({wordlist_path})"
        command.extend(["-a", "0", hash_path, wordlist_path])

    command.extend(["--potfile-disable", "--quiet", "--hwmon-disable"])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    # Hashcat return codes:
    # 0: Password found
    # 1: Password not found
    # -1/255: Error
    if process.returncode == 0:
        # On success, Hashcat outputs the hash:password.
        # Since we are using --quiet, it should only be the result line.
        output = stdout.decode().strip()
        if ":" in output:
            password = output.split(":")[-1]
            jobs[job_id]["status"] = "cracked"
            jobs[job_id]["result"] = password
            return

    if process.returncode == 1:
        jobs[job_id]["status"] = "not_cracked"
        if attack_mode == "bruteforce":
            jobs[job_id]["result"] = f"Password not found with brute force mask '{mask}'."
        else:
            jobs[job_id]["result"] = "Password not found in the provided wordlist."
        return

    # Failure
    error_output = stderr.decode().strip() or stdout.decode().strip()
    jobs[job_id]["status"] = "failed"
    jobs[job_id]["result"] = f"Hashcat failed (Exit Code {process.returncode}). Output: {error_output}"


async def start_cracking_task(
    job_id: str,
    engine: str,
    hash_path: str,
    wordlist_id: str,
    hashcat_mode: int | None,
    hashcat_attack: str = "wordlist",
    hashcat_mask: str | None = None,
):
    """
    The main background task that orchestrates the cracking process and final cleanup.
    """
    try:
        if engine == "john":
            wordlist_path = WORDLISTS.get(wordlist_id)
            if not wordlist_path or not os.path.exists(wordlist_path):
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["result"] = f"Wordlist '{wordlist_id}' not found on server."
                return

            await _run_john(job_id, hash_path, wordlist_path)
        elif engine == "hashcat":
            if hashcat_mode is None:
                 jobs[job_id]["status"] = "failed"
                 jobs[job_id]["result"] = "Hashcat mode is required."
            else:
                wordlist_path = None
                if hashcat_attack != "bruteforce":
                    wordlist_path = WORDLISTS.get(wordlist_id)
                    if not wordlist_path or not os.path.exists(wordlist_path):
                        jobs[job_id]["status"] = "failed"
                        jobs[job_id]["result"] = f"Wordlist '{wordlist_id}' not found on server."
                        return

                await _run_hashcat(
                    job_id,
                    hash_path,
                    hashcat_mode,
                    wordlist_path=wordlist_path,
                    attack_mode=hashcat_attack,
                    mask=hashcat_mask,
                )
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Invalid cracking engine specified."

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = f"An unexpected error occurred: {str(e)}"
    finally:
        # Final step of SanitizationTask: clean up the temporary hash file.
        if os.path.exists(hash_path):
            os.remove(hash_path)
