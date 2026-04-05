import json
import mimetypes
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
SUBMISSIONS_PATH = DATA_DIR / "submissions.jsonl"
ALLOWED_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/simulation.html": "simulation.html",
    "/research.html": "research.html",
    "/solutions.html": "solutions.html",
    "/community.html": "community.html",
    "/connect.html": "connect.html",
    "/styles.css": "styles.css",
    "/script.js": "script.js",
}


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SUBMISSIONS_PATH.touch(exist_ok=True)


def save_submission(payload: dict) -> None:
    ensure_data_dir()
    with SUBMISSIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def maybe_send_email(payload: dict) -> tuple[bool, str]:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    inbox = os.getenv("INBOX_EMAIL")
    from_email = os.getenv("FROM_EMAIL", smtp_user or "")

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, inbox, from_email]):
        return False, "Email forwarding is not configured yet."

    message = EmailMessage()
    message["Subject"] = f"Silent Thirst inquiry: {payload['interest']}"
    message["From"] = from_email
    message["To"] = inbox
    message["Reply-To"] = payload["email"]
    message.set_content(
        "\n".join(
            [
                "New website submission",
                f"Submitted at: {payload['submittedAt']}",
                f"Name: {payload['name']}",
                f"Email: {payload['email']}",
                f"Interest: {payload['interest']}",
                "",
                "Message:",
                payload["message"],
            ]
        )
    )

    with smtplib.SMTP(smtp_host, int(smtp_port), timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

    return True, f"Forwarded to {inbox}."


class PassionProjectHandler(BaseHTTPRequestHandler):
    server_version = "SilentThirstServer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self.respond_json(200, {"status": "ok"})
            return

        if parsed.path == "/api/submissions":
            self.handle_submissions_feed()
            return

        file_name = ALLOWED_FILES.get(parsed.path)
        if not file_name:
            self.respond_json(404, {"error": "Not found"})
            return

        self.serve_file(ROOT / file_name)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path != "/api/contact":
            self.respond_json(404, {"error": "Not found"})
            return

        try:
            payload = self.read_request_payload()
            submission = self.validate_submission(payload)
            save_submission(submission)
            emailed, email_note = maybe_send_email(submission)
            self.respond_json(
                200,
                {
                    "ok": True,
                    "message": "Submission received.",
                    "emailed": emailed,
                    "delivery": email_note,
                    "submission": submission,
                },
            )
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # pragma: no cover
            self.respond_json(500, {"ok": False, "error": f"Server error: {exc}"})

    def serve_file(self, path: Path) -> None:
        if not path.exists():
            self.respond_json(404, {"error": "File not found"})
            return

        mime_type, _ = mimetypes.guess_type(path.name)
        content_type = mime_type or "application/octet-stream"
        content = path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_request_payload(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")

        if "application/json" in content_type:
            return json.loads(raw_body or "{}")

        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(raw_body, keep_blank_values=True)
            return {key: values[0] for key, values in parsed.items()}

        raise ValueError("Unsupported content type.")

    def validate_submission(self, payload: dict) -> dict:
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip()
        interest = str(payload.get("interest", "")).strip()
        message = str(payload.get("message", "")).strip()

        if not name:
            raise ValueError("Name is required.")
        if not email or "@" not in email:
            raise ValueError("A valid email is required.")
        if not interest:
            raise ValueError("Interest selection is required.")
        if not message:
            raise ValueError("Message is required.")

        return {
            "name": name,
            "email": email,
            "interest": interest,
            "message": message,
            "submittedAt": datetime.now(timezone.utc).isoformat(),
        }

    def handle_submissions_feed(self) -> None:
        ensure_data_dir()
        entries = []
        with SUBMISSIONS_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    raw = json.loads(line)
                    first_name = raw.get("name", "Someone").split()[0]
                    entries.append(
                        {
                            "name": first_name,
                            "interest": raw.get("interest", ""),
                            "submittedAt": raw.get("submittedAt", ""),
                        }
                    )
        self.respond_json(200, {"submissions": list(reversed(entries[-8:]))})

    def respond_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    load_dotenv()
    ensure_data_dir()
    port = int(os.getenv("PORT", "4173"))
    server = ThreadingHTTPServer(("0.0.0.0", port), PassionProjectHandler)
    print(f"Serving The Silent Thirst on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
