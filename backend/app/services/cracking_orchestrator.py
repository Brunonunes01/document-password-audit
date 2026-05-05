# backend/app/services/cracking_orchestrator.py
import asyncio
import os
from typing import Dict

from app.config import JOHN_PATH, HASHCAT_PATH, WORDLISTS, SUPPORTED_FORMATS

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

        password = line.split(":")[1].strip()
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
    file_type: str | None = None,
    charset: str = "?d",
    min_length: int | None = None,
    max_length: int | None = None,
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

    if attack_mode == "bruteforce_range":
        if not min_length or not max_length:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Minimum and maximum lengths are required for brute force range mode."
            return
        if min_length < 1 or max_length < min_length or max_length > 12:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Invalid brute force range. Use minimum >= 1, maximum >= minimum, and maximum <= 12."
            return
    elif attack_mode == "bruteforce":
        if not mask:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Hashcat mask is required for brute force mode."
            return
    else:
        if not wordlist_path:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = "Wordlist is required for Hashcat wordlist mode."
            return

    format_config = SUPPORTED_FORMATS.get(file_type or "")
    fallback_modes = list(format_config.get("hashcat_modes", [])) if format_config else []
    modes_to_try = [hashcat_mode] + [mode for mode in fallback_modes if mode != hashcat_mode]

    no_hash_modes: list[int] = []

    masks_to_try = [mask]
    if attack_mode == "bruteforce_range":
        masks_to_try = [charset * length for length in range(min_length or 1, (max_length or 1) + 1)]

    for mode in modes_to_try:
        mode_loaded_hash = False
        for current_mask in masks_to_try:
            command = [HASHCAT_PATH, "-m", str(mode)]

            if attack_mode in ["bruteforce", "bruteforce_range"]:
                if attack_mode == "bruteforce_range":
                    jobs[job_id]["attack"] = (
                        f"hashcat brute force range ({charset}, {min_length}-{max_length}) "
                        f"testing length {len(current_mask or '') // len(charset)} mode {mode}"
                    )
                else:
                    jobs[job_id]["attack"] = f"hashcat brute force ({current_mask}) mode {mode}"
                command.extend(["-a", "3", hash_path, current_mask or ""])
            else:
                jobs[job_id]["attack"] = f"hashcat wordlist ({wordlist_path}) mode {mode}"
                command.extend(["-a", "0", hash_path, wordlist_path])

            command.extend(["--potfile-disable", "--quiet", "--hwmon-disable"])

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output_text = stderr.decode().strip() or stdout.decode().strip()

            if process.returncode == 0:
                output = stdout.decode().strip()
                if ":" in output:
                    password = output.split(":")[-1]
                    jobs[job_id]["status"] = "cracked"
                    jobs[job_id]["result"] = password
                    return

            if process.returncode == 1:
                mode_loaded_hash = True
                continue

            if "No hashes loaded" in output_text or "Signature unmatched" in output_text:
                no_hash_modes.append(mode)
                break

            jobs[job_id]["status"] = "failed"
            jobs[job_id]["result"] = f"Hashcat failed (Exit Code {process.returncode}) using mode {mode}. Output: {output_text}"
            return

        if mode_loaded_hash:
            jobs[job_id]["status"] = "not_cracked"
            if attack_mode == "bruteforce_range":
                jobs[job_id]["result"] = (
                    f"Password not found with brute force range '{charset}' from "
                    f"{min_length} to {max_length} using Hashcat mode {mode}."
                )
            elif attack_mode == "bruteforce":
                jobs[job_id]["result"] = f"Password not found with brute force mask '{mask}' using Hashcat mode {mode}."
            else:
                jobs[job_id]["result"] = f"Password not found in the provided wordlist using Hashcat mode {mode}."
            return

    jobs[job_id]["status"] = "failed"
    jobs[job_id]["result"] = (
        "Hashcat could not load the hash with the tested modes: "
        f"{', '.join(str(mode) for mode in no_hash_modes)}. "
        "The file may use a different encryption variant; try John or identify the correct Hashcat mode manually."
    )


async def start_cracking_task(
    job_id: str,
    engine: str,
    hash_path: str,
    wordlist_id: str,
    hashcat_mode: int | None,
    hashcat_attack: str = "wordlist",
    hashcat_mask: str | None = None,
    file_type: str | None = None,
    hashcat_charset: str = "?d",
    hashcat_min_length: int | None = None,
    hashcat_max_length: int | None = None,
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
                if hashcat_attack not in ["bruteforce", "bruteforce_range"]:
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
                    file_type=file_type,
                    charset=hashcat_charset,
                    min_length=hashcat_min_length,
                    max_length=hashcat_max_length,
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
