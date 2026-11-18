"""Step 1: download the source PDF once and verify its checksum."""

import hashlib
import urllib.request

import config


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_pdf() -> None:
    """Reuse the local PDF when it is intact, otherwise download it."""
    if config.PDF_PATH.exists():
        if sha256_of(config.PDF_PATH.read_bytes()) == config.PDF_SHA256:
            print(f"Using existing PDF: {config.PDF_PATH.name}")
            return
        raise ValueError(f"{config.PDF_PATH} does not match the expected checksum.")

    request = urllib.request.Request(
        config.PDF_URL, headers={"User-Agent": "tax-expenditure-extractor/0.1"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()

    # Stop here if the publisher changed the file: page numbers may have moved.
    if sha256_of(data) != config.PDF_SHA256:
        raise ValueError("Downloaded PDF does not match the expected checksum.")

    config.PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.PDF_PATH.write_bytes(data)
    print(f"Downloaded PDF: {config.PDF_PATH.name}")
