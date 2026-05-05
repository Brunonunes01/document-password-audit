# PDF Cracker - Project Instructions

## Overview
This project is a web-based service for extracting and cracking password-protected PDF files using John the Ripper (Jumbo) and Hashcat.

## Dependencies
The project relies on several system-level tools:
- **John the Ripper (Jumbo Version):** Required for PDF hash extraction (`pdf2john.pl`) and CPU-based cracking.
- **Hashcat:** Optional engine for GPU/CPU-based cracking.
- **Wordlists:** A `rockyou.txt` file is expected at `/usr/share/wordlists/rockyou.txt`.

## Local Setup (John Jumbo)
To ensure PDF support, a local installation of John Jumbo is recommended. The project is configured to look for it at:
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
    - `secure_upload`: Handles temporary PDF storage.
    - `hash_extraction`: Uses `pdf2john.pl` to get hashes.
    - `cracking_orchestrator`: Manages background tasks for John and Hashcat.
- **Frontend:** Single-page Vanilla JS interface in `app/static/index.html`.

## Configuration
Paths for executables and wordlists are managed in `app/config.py`. It prioritizes local installations in the `tools` directory over system binaries.
