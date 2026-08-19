from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def build_slides_client(credentials: Credentials):
    return build("slides", "v1", credentials=credentials)


def build_drive_client(credentials: Credentials):
    return build("drive", "v3", credentials=credentials)
