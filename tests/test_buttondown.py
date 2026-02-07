from unittest.mock import MagicMock, patch

from monologue_tools.buttondown import ButtondownClient


@patch("monologue_tools.buttondown.requests.Session")
def test_list_drafts(MockSession):
    mock_session = MockSession.return_value
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"id": "abc", "subject": "2025-01-15 Hello", "status": "draft"},
            {"id": "def", "subject": "2025-01-16 World", "status": "draft"},
            {"id": "ghi", "subject": "No date here", "status": "draft"},
            {"id": "jkl", "subject": "2025-01-17 Sent", "status": "sent"},
        ]
    }
    mock_session.get.return_value = mock_resp

    client = ButtondownClient("test-key")
    drafts = client.list_drafts()

    mock_session.get.assert_called_once_with(
        "https://api.buttondown.email/v1/emails?status=draft"
    )
    assert "2025-01-15" in drafts
    assert drafts["2025-01-15"]["id"] == "abc"
    assert "2025-01-16" in drafts
    # No date -> excluded
    assert len([k for k in drafts if drafts[k]["id"] == "ghi"]) == 0
    # status=sent -> excluded
    assert "2025-01-17" not in drafts


@patch("monologue_tools.buttondown.requests.Session")
def test_create_draft(MockSession):
    mock_session = MockSession.return_value
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "new-id", "status": "draft"}
    mock_session.post.return_value = mock_resp

    client = ButtondownClient("test-key")
    result = client.create_draft("2025-01-15 Test", "Body text")

    mock_session.post.assert_called_once_with(
        "https://api.buttondown.email/v1/emails",
        json={"subject": "2025-01-15 Test", "body": "Body text", "status": "draft"},
    )
    assert result["id"] == "new-id"


@patch("monologue_tools.buttondown.requests.Session")
def test_update_draft(MockSession):
    mock_session = MockSession.return_value
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "existing-id", "status": "draft"}
    mock_session.patch.return_value = mock_resp

    client = ButtondownClient("test-key")
    result = client.update_draft("existing-id", "2025-01-15 Updated", "New body")

    mock_session.patch.assert_called_once_with(
        "https://api.buttondown.email/v1/emails/existing-id",
        json={
            "subject": "2025-01-15 Updated",
            "body": "New body",
            "status": "draft",
        },
    )
    assert result["id"] == "existing-id"


@patch("monologue_tools.buttondown.requests.Session")
def test_publish_creates_new_when_no_existing_draft(MockSession):
    mock_session = MockSession.return_value

    # list_drafts returns empty
    mock_list_resp = MagicMock()
    mock_list_resp.json.return_value = {"results": []}
    mock_session.get.return_value = mock_list_resp

    # create_draft response
    mock_create_resp = MagicMock()
    mock_create_resp.json.return_value = {"id": "brand-new", "status": "draft"}
    mock_session.post.return_value = mock_create_resp

    client = ButtondownClient("test-key")
    result = client.publish("2025-01-20 New Entry", "Content here")

    mock_session.post.assert_called_once()
    assert result["id"] == "brand-new"


@patch("monologue_tools.buttondown.requests.Session")
def test_publish_updates_existing_draft_when_date_matches(MockSession):
    mock_session = MockSession.return_value

    # list_drafts returns a matching draft
    mock_list_resp = MagicMock()
    mock_list_resp.json.return_value = {
        "results": [
            {"id": "old-draft", "subject": "2025-01-20 Old Title", "status": "draft"}
        ]
    }
    mock_session.get.return_value = mock_list_resp

    # update_draft response
    mock_update_resp = MagicMock()
    mock_update_resp.json.return_value = {"id": "old-draft", "status": "draft"}
    mock_session.patch.return_value = mock_update_resp

    client = ButtondownClient("test-key")
    result = client.publish("2025-01-20 Updated Entry", "Updated content")

    mock_session.patch.assert_called_once_with(
        "https://api.buttondown.email/v1/emails/old-draft",
        json={
            "subject": "2025-01-20 Updated Entry",
            "body": "Updated content",
            "status": "draft",
        },
    )
    assert result["id"] == "old-draft"
