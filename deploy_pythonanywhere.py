#!/usr/bin/env python3
"""Deploy vema to PythonAnywhere using the PA API.

Required environment variables:
  PA_USERNAME   - your PythonAnywhere username
  PA_API_TOKEN  - API token from Account -> API token tab
  PA_HOST       - optional: www.pythonanywhere.com (default) or eu.pythonanywhere.com

Usage:
  set PA_USERNAME=yourname
  set PA_API_TOKEN=your-token
  python deploy_pythonanywhere.py
"""
import os
import sys
import time

import requests

REPO_URL = "https://github.com/bunny7200d-bit/vema.git"
PROJECT_DIR = "vema"
PYTHON_VERSION = "python310"


def env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default).strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def api(method: str, url: str, token: str, **kwargs):
    headers = {"Authorization": f"Token {token}"}
    response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    return response


def run_console_command(host: str, username: str, token: str, command: str, wait: float = 3.0) -> str:
    base = f"https://{host}/api/v0/user/{username}/consoles/"
    create = api("POST", base, token, data={"executable": "bash", "arguments": ""})
    if create.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create console: {create.status_code} {create.text}")

    console_id = create.json()["id"]
    send_url = f"{base}{console_id}/send_input/"
    send = api("POST", send_url, token, data={"input": command + "\n"})
    if send.status_code != 200:
        raise RuntimeError(f"Failed to send command: {send.status_code} {send.text}")

    time.sleep(wait)
    out = api("GET", f"{base}{console_id}/get_latest_output/", token)
    if out.status_code != 200:
        raise RuntimeError(f"Failed to read output: {out.status_code} {out.text}")
    return out.text


def upload_file(host: str, username: str, token: str, remote_path: str, content: bytes):
    url = f"https://{host}/api/v0/user/{username}/files/path{remote_path}"
    response = api("POST", url, token, files={"content": content})
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed for {remote_path}: {response.status_code} {response.text}")


def ensure_webapp(host: str, username: str, token: str, domain: str):
    base = f"https://{host}/api/v0/user/{username}/webapps/"
    existing = api("GET", base, token)
    if existing.status_code != 200:
        raise RuntimeError(f"Failed to list webapps: {existing.status_code} {existing.text}")

    domains = [item.get("domain_name") for item in existing.json()]
    if domain not in domains:
        create = api("POST", base, token, data={"domain_name": domain, "python_version": PYTHON_VERSION})
        if create.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create webapp: {create.status_code} {create.text}")

    webapp_url = f"{base}{domain}/"
    patch = api(
        "PATCH",
        webapp_url,
        token,
        data={
            "virtualenv_path": f"/home/{username}/{PROJECT_DIR}/venv",
        },
    )
    if patch.status_code not in (200, 201):
        raise RuntimeError(f"Failed to configure webapp: {patch.status_code} {patch.text}")


def ensure_static_mapping(host: str, username: str, token: str, domain: str):
    base = f"https://{host}/api/v0/user/{username}/webapps/{domain}/static_files/"
    mappings = api("GET", base, token)
    if mappings.status_code != 200:
        raise RuntimeError(f"Failed to list static files: {mappings.status_code} {mappings.text}")

    target_url = "/static/"
    target_path = f"/home/{username}/{PROJECT_DIR}/app/static"
    for item in mappings.json():
        if item.get("url") == target_url and item.get("path") == target_path:
            return

    create = api("POST", base, token, data={"url": target_url, "path": target_path})
    if create.status_code not in (200, 201):
        raise RuntimeError(f"Failed to add static mapping: {create.status_code} {create.text}")


def reload_webapp(host: str, username: str, token: str, domain: str):
    url = f"https://{host}/api/v0/user/{username}/webapps/{domain}/reload/"
    response = api("POST", url, token)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to reload webapp: {response.status_code} {response.text}")


DEFAULT_USERNAME = "vemahomeappliances"


def main():
    username = os.environ.get("PA_USERNAME", DEFAULT_USERNAME).strip() or DEFAULT_USERNAME
    token = env("PA_API_TOKEN")
    host = os.environ.get("PA_HOST", "www.pythonanywhere.com").strip() or "www.pythonanywhere.com"
    domain = f"{username}.pythonanywhere.com"
    if host.startswith("eu."):
        domain = f"{username}.eu.pythonanywhere.com"

    home = f"/home/{username}"
    project = f"{home}/{PROJECT_DIR}"

    print(f"Deploying to https://{domain}")

    print("1/6 Cloning or updating repository...")
    run_console_command(
        host,
        username,
        token,
        f"cd {home} && (test -d {PROJECT_DIR} && cd {PROJECT_DIR} && git pull || git clone {REPO_URL})",
        wait=8,
    )

    print("2/6 Creating virtualenv and installing dependencies...")
    run_console_command(
        host,
        username,
        token,
        f"cd {project} && python3.10 -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
        wait=15,
    )

    print("3/6 Creating .env if missing...")
    run_console_command(
        host,
        username,
        token,
        f"cd {project} && test -f .env || cp .env.example .env",
        wait=2,
    )

    print("4/6 Seeding demo data...")
    run_console_command(
        host,
        username,
        token,
        f"cd {project} && source venv/bin/activate && python create_demo.py",
        wait=5,
    )

    print("5/6 Configuring web app and WSGI...")
    ensure_webapp(host, username, token, domain)
    ensure_static_mapping(host, username, token, domain)

    wsgi_path = f"/var/www/{username}_{domain.replace('.', '_')}_wsgi.py"
    wsgi_content = f"""import sys

path = '{project}'
if path not in sys.path:
    sys.path.insert(0, path)

from wsgi import application
""".encode("utf-8")
    upload_file(host, username, token, wsgi_path, wsgi_content)

    print("6/6 Reloading web app...")
    reload_webapp(host, username, token, domain)

    print(f"Done. Open https://{domain}")
    print("Login: admin@example.com / adminpass")


if __name__ == "__main__":
    main()
