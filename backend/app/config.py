import os
import shutil
from pathlib import Path

"""
Centralized configuration for the application.
"""

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_JOHN_RUN = PROJECT_ROOT / "tools" / "john" / "run"


def first_existing_path(paths: list[str]) -> str | None:
    for path in paths:
        if os.path.isfile(path):
            return path
    return None


def executable_path(env_name: str, binary_name: str, fallback_paths: list[str]) -> str:
    env_path = os.environ.get(env_name)
    if env_path:
        return env_path

    # Prioritize fallback paths (like local installations) over system PATH
    local_path = first_existing_path(fallback_paths)
    if local_path:
        return local_path

    path_from_shell = shutil.which(binary_name)
    if path_from_shell:
        return path_from_shell

    return fallback_paths[0]


def script_path(env_name: str, fallback_paths: list[str]) -> str:
    env_path = os.environ.get(env_name)
    if env_path:
        return env_path

    return first_existing_path(fallback_paths) or fallback_paths[0]


# --- Path Configuration ---
PDF2JOHN_PATH = script_path(
    "PDF2JOHN_PATH",
    [
        str(LOCAL_JOHN_RUN / "pdf2john.pl"),
        str(LOCAL_JOHN_RUN / "pdf2john.py"),
        "/usr/share/john/pdf2john.pl",
        "/usr/share/john/pdf2john.py",
        "/usr/local/bin/pdf2john.pl",
        "/usr/bin/pdf2john",
    ],
)
JOHN_PATH = executable_path("JOHN_PATH", "john", [str(LOCAL_JOHN_RUN / "john"), "/usr/bin/john", "/usr/sbin/john"])
HASHCAT_PATH = executable_path("HASHCAT_PATH", "hashcat", ["/usr/bin/hashcat", "/usr/sbin/hashcat"])

# --- Wordlist Configuration ---
# Maps a friendly name to the absolute path of the wordlist file.
# In a real app, this could be more dynamic (e.g., scanning a directory).
DEFAULT_WORDLIST_PATH = first_existing_path(
    [
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/john/password.lst",
    ]
) or "/usr/share/wordlists/rockyou.txt"

WORDLISTS = {
    "rockyou": os.environ.get("WORDLIST_ROCKYOU", "/usr/share/wordlists/rockyou.txt"),
    "john-default": os.environ.get("WORDLIST_JOHN_DEFAULT", DEFAULT_WORDLIST_PATH),
}


# --- Verification ---
def check_executable(name: str, path: str):
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        print(
            f"WARNING: Executable '{name}' not found or not executable at '{path}'. "
            f"Please install it or set the corresponding environment variable."
        )

def check_file(name: str, path: str):
    if not os.path.isfile(path):
        print(
            f"WARNING: File '{name}' not found at '{path}'. "
            f"Please install it or set the corresponding environment variable."
        )

check_file("pdf2john", PDF2JOHN_PATH)
check_executable("john", JOHN_PATH)
check_executable("hashcat", HASHCAT_PATH)

for wordlist_name, wordlist_path in WORDLISTS.items():
    if not os.path.isfile(wordlist_path):
        print(f"WARNING: Wordlist '{wordlist_name}' not found at '{wordlist_path}'.")
