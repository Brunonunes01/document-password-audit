# Document Password Audit - Project Instructions

## Overview
This project is a local web service for auditing password-protected documents. It extracts hashes from supported files and tries to recover passwords with John the Ripper Jumbo or Hashcat.

Supported formats:
- PDF (`.pdf`)
- ZIP (`.zip`)
- Microsoft Office (`.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`)

## Dependencies
The project relies on several system-level tools:
- **John the Ripper (Jumbo Version):** Required for CPU-based cracking and `*2john` extractors.
- **Extractors:** `pdf2john.pl`, `zip2john`, and `office2john.py`.
- **Hashcat:** Optional engine for GPU/CPU-based cracking.
- **Wordlists:** A `rockyou.txt` file is expected at `/usr/share/wordlists/rockyou.txt`.

## Local Setup (John Jumbo)
To ensure extractor support, a local installation of John Jumbo is recommended. The project is configured to look for it at:
`../tools/john/run/john`

### Installation Steps:
```bash
sudo apt-get install -y build-essential libssl-dev zlib1g-dev yasm pkg-config libgmp-dev libpcap-dev libbz2-dev
mkdir -p ../tools
git clone https://github.com/openwall/john.git ../tools/john
cd ../tools/john/src
./configure
make -s clean
make -sj"$(nproc)"
```

## Architecture
- **Backend:** FastAPI (Python 3.12).
- **Services:**
    - `secure_upload`: Handles temporary uploaded file storage.
    - `hash_extraction`: Runs the configured extractor for each supported file type.
    - `cracking_orchestrator`: Manages background jobs for John and Hashcat, including Hashcat mode fallback.
- **Frontend:** Single-page Vanilla JS interface in `app/static/index.html`.

## Configuration
Paths for executables and wordlists are managed in `app/config.py`. It prioritizes local installations in the `tools` directory over system binaries.

Relevant environment variables:
- `PDF2JOHN_PATH`
- `ZIP2JOHN_PATH`
- `OFFICE2JOHN_PATH`
- `JOHN_PATH`
- `HASHCAT_PATH`
- `WORDLIST_ROCKYOU`
- `WORDLIST_JOHN_DEFAULT`
