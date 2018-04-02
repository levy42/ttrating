from app import app
import pytest

client = app.test_client()


def test_sample():
    with pytest.raises(Exception):
        client.get('/')
