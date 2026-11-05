"""Exercise the actual Gunicorn entry point inside the built Linux container."""

import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request


def main():
    env = {
        **os.environ,
        "PORT": "8099",
        "K_SERVICE": "container-smoke",
        "DEBUG": "false",
        "SECRET_KEY": secrets.token_urlsafe(64),
        "ALLOWED_HOSTS": "127.0.0.1",
    }
    process = subprocess.Popen(
        ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"], env=env
    )
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Gunicorn exited before becoming healthy")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8099/api/health", timeout=1) as res:
                    assert res.status == 200
                    assert json.load(res) == {"status": "ok"}
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        else:
            raise RuntimeError("Health endpoint did not become ready")
        request = urllib.request.Request(
            "http://127.0.0.1:8099/api/health", headers={"X-Forwarded-Proto": "https"}
        )
        with urllib.request.urlopen(request, timeout=2) as res:
            assert res.headers["X-Frame-Options"] == "DENY"
            assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
        assert os.getuid() != 0, "Container must run as non-root"
        print("PASS: non-root Gunicorn, custom PORT, health JSON, proxy HTTPS and security headers")
    finally:
        process.terminate()
        process.wait(timeout=15)


if __name__ == "__main__":
    main()
