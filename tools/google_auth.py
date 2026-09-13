from pathlib import Path


CONFIG_DIR = Path.home() / ".bchubot"
CREDENTIALS_PATH = CONFIG_DIR / "google_credentials.json"
TOKEN_PATH = CONFIG_DIR / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]


class GoogleAuthError(Exception):
    pass


def get_credentials():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GoogleAuthError(
            "Google libraries are not installed. Activate BchuBot-env and run "
            "pip install google-api-python-client google-auth-httplib2 "
            "google-auth-oauthlib."
        ) from exc

    if not CREDENTIALS_PATH.exists():
        raise GoogleAuthError(
            "Google access is not set up. Enable the Calendar and Tasks APIs "
            "in Google Cloud, create a Desktop OAuth client, and save the "
            f"JSON file to {CREDENTIALS_PATH}."
        )

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
        TOKEN_PATH.chmod(0o600)

    return creds


def calendar_service():
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=get_credentials())


def tasks_service():
    from googleapiclient.discovery import build

    return build("tasks", "v1", credentials=get_credentials())
