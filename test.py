from app import app, db
from models import WorldRating
import pytest

client = app.test_client()

def test_sample():
    with pytest.raises(Exception):
        res = client.get('/')


with app.app_context():
    print(WorldRating.query.get(55))
