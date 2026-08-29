
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import get_dashboard_data, DashboardChat
from datetime import datetime

# Mock the database context manager
class MockCursorContext:
    def __init__(self, mock_cursor):
        self.mock_cursor = mock_cursor

    async def __aenter__(self):
        return self.mock_cursor

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
async def test_get_dashboard_data_optimized():
    """
    Test that get_dashboard_data uses a single efficient query.
    """
    mock_cursor = AsyncMock()

    # Setup mock data reflecting the result of the new single query
    # Columns:
    # 0: id
    # 1: title
    # 2: total_messages
    # 3: today_messages
    # 4: last_message_text
    # 5: last_message_author
    # 6: last_message_at
    # 7: top_users (list of dicts)

    mock_rows = [
        (
            1, "Chat 1", 100, 10,
            "Hello", "User1", datetime(2023, 1, 1),
            [{"name": "User1", "count": 5}]
        ),
        (
            2, "Chat 2", 50, 5,
            "Hi", "User2", datetime(2023, 1, 2),
            [{"name": "User2", "count": 3}]
        ),
        (
            3, "Chat 3", 20, 0,
            None, None, None,
            []
        ),
    ]

    mock_cursor.fetchall.return_value = mock_rows

    with patch('app.models.get_cursor', return_value=MockCursorContext(mock_cursor)):
        results = await get_dashboard_data()

        assert len(results) == 3

        # Verify Chat 1
        assert results[0].title == "Chat 1"
        assert results[0].total_messages == 100
        assert results[0].last_message_text == "Hello"
        assert results[0].top_users == [{"name": "User1", "count": 5}]

        # Verify Chat 2
        assert results[1].title == "Chat 2"
        assert results[1].last_message_text == "Hi"

        # Verify Chat 3 (empty edge cases)
        assert results[2].title == "Chat 3"
        assert results[2].last_message_text is None
        assert results[2].top_users == []

        # Verify only 1 query was executed
        assert mock_cursor.execute.call_count == 1
        print(f"Executed {mock_cursor.execute.call_count} query for 3 chats.")
