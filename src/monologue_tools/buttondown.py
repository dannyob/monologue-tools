import re

import requests


class ButtondownClient:
    BASE_URL = "https://api.buttondown.email/v1"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {api_key}"})

    def list_drafts(self) -> dict[str, dict]:
        resp = self.session.get(f"{self.BASE_URL}/emails?status=draft")
        resp.raise_for_status()
        drafts = {}
        for email in resp.json()["results"]:
            if email["status"] == "draft":
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", email["subject"])
                if date_match:
                    drafts[date_match.group(0)] = email
        return drafts

    def create_draft(self, subject: str, body: str) -> dict:
        resp = self.session.post(
            f"{self.BASE_URL}/emails",
            json={"subject": subject, "body": body, "status": "draft"},
        )
        resp.raise_for_status()
        return resp.json()

    def update_draft(self, email_id: str, subject: str, body: str) -> dict:
        resp = self.session.patch(
            f"{self.BASE_URL}/emails/{email_id}",
            json={"subject": subject, "body": body, "status": "draft"},
        )
        resp.raise_for_status()
        return resp.json()

    def publish(self, subject: str, body: str) -> dict:
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", subject)
        if date_match:
            drafts = self.list_drafts()
            iso_date = date_match.group(0)
            if iso_date in drafts:
                return self.update_draft(drafts[iso_date]["id"], subject, body)
        return self.create_draft(subject, body)
