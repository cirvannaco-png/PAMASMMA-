#!/usr/bin/env python3
"""Publish PAMASMMA's frontend to a Hugging Face Docker Space.

Usage from the repository root with a write token in HF_TOKEN:
    python -m pip install huggingface_hub
    export HF_TOKEN=hf_...
    python deploy_space.py --space YOUR_HF_USER/pamasmma \
        --api-url https://pamasmma-api.onrender.com/api/v1
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

HERE = Path(__file__).resolve().parent
SPACE_FILES = HERE / "hf-space"
IGNORE = shutil.ignore_patterns("node_modules", ".next", ".git", ".env*", "*.log")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="owner/name of the Space")
    ap.add_argument("--api-url", required=True, help="Public PAMASMMA API base URL")
    ap.add_argument("--frontend", default="frontend", help="Path to the frontend dir")
    ap.add_argument("--private", action="store_true", help="Create the Space as private")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Set HF_TOKEN to a Hugging Face token with write access.", file=sys.stderr)
        return 1
    if not args.api_url.startswith("https://"):
        print("--api-url must be https:// (browsers block mixed content).", file=sys.stderr)
        return 1
    frontend = Path(args.frontend)
    if not (frontend / "package.json").exists():
        print(f"{frontend}/package.json not found — run from the repo root.", file=sys.stderr)
        return 1
    for required in ("Dockerfile", "README.md"):
        if not (SPACE_FILES / required).is_file():
            print(f"Required deployment file missing: {SPACE_FILES / required}", file=sys.stderr)
            return 1

    api = HfApi(token=token)
    api.create_repo(
        repo_id=args.space, repo_type="space", space_sdk="docker",
        private=args.private, exist_ok=True,
    )
    # Space variables are exposed to Docker builds as build args and at runtime.
    # Next.js inlines NEXT_PUBLIC_API_URL at build time, so this variable must
    # exist before the upload triggers the Space build.
    api.add_space_variable(args.space, "NEXT_PUBLIC_API_URL", args.api_url)

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        shutil.copytree(frontend, stage, ignore=IGNORE)
        shutil.copy(SPACE_FILES / "Dockerfile", stage / "Dockerfile")
        shutil.copy(SPACE_FILES / "README.md", stage / "README.md")
        api.upload_folder(
            repo_id=args.space, repo_type="space", folder_path=str(stage),
            commit_message="Deploy PAMASMMA frontend",
        )

    owner, name = args.space.split("/", 1)
    host = f"{owner}-{name}".lower().replace("_", "-").replace(".", "-")
    print(f"\nSpace:  https://huggingface.co/spaces/{args.space}")
    print(f"Direct: https://{host}.hf.space   <-- use THIS URL (not the huggingface.co page)")
    print("Now set WEBAUTHN_RP_ID / WEBAUTHN_ORIGIN / ALLOWED_ORIGINS on the Render API to match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
