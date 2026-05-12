"""Tests for WikiService using MockFeishuClient."""

import pytest
from feishu_kit.modules.wiki import WikiService


@pytest.fixture
def wiki(mock_client):
    return WikiService(mock_client)


@pytest.mark.asyncio
async def test_list_spaces(wiki, mock_client):
    mock_client.set_response("/wiki/v2/spaces", {
        "code": 0,
        "data": {
            "items": [
                {"space_id": "123", "name": "Test Space"},
            ],
            "has_more": False,
        },
    })

    result = await wiki.list_spaces()
    assert result["code"] == 0
    assert len(result["data"]["items"]) == 1
    assert result["data"]["items"][0]["name"] == "Test Space"

    # Verify the call
    call = mock_client.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/wiki/v2/spaces"


@pytest.mark.asyncio
async def test_create_node(wiki, mock_client):
    mock_client.set_response("/wiki/v2/spaces/space123/nodes", {
        "code": 0,
        "data": {
            "node": {
                "node_token": "node_abc",
                "obj_token": "obj_xyz",
                "title": "New Doc",
            },
        },
    })

    result = await wiki.create_node("space123", title="New Doc")
    assert result["code"] == 0
    assert result["data"]["node"]["node_token"] == "node_abc"

    call = mock_client.calls[0]
    assert call["method"] == "POST"
    assert call["json"]["title"] == "New Doc"


@pytest.mark.asyncio
async def test_rename_node(wiki, mock_client):
    result = await wiki.rename_node("space123", "node_abc", "New Title")
    call = mock_client.calls[0]
    assert call["method"] == "POST"
    assert "update_title" in call["path"]
    assert call["json"]["title"] == "New Title"


@pytest.mark.asyncio
async def test_get_doc_raw_content(wiki, mock_client):
    mock_client.set_response("/docx/v1/documents/obj123/raw_content", {
        "code": 0,
        "data": {"content": "Hello world"},
    })

    result = await wiki.get_doc_raw_content("obj123")
    assert result["data"]["content"] == "Hello world"


@pytest.mark.asyncio
async def test_search_nodes(wiki, mock_client):
    mock_client.set_response("/wiki/v2/spaces/space123/nodes", {
        "code": 0,
        "data": {
            "items": [
                {"title": "Introduction to AI", "node_token": "n1"},
                {"title": "Robotics Basics", "node_token": "n2"},
                {"title": "AI Ethics", "node_token": "n3"},
            ],
            "has_more": False,
        },
    })

    matches = await wiki.search_nodes("space123", "AI")
    assert len(matches) == 2
    titles = [m["title"] for m in matches]
    assert "Introduction to AI" in titles
    assert "AI Ethics" in titles
