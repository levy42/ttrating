from app import app
from models import db, Player

client = app.test_client()
app.testing = True


def _create_test_player():
    player = Player()
    player.name = 'Якийсь хер'
    player.city = 'Львів'
    player.external_id = 10000000
    db.session.add(player)
    db.session.commit()
    return player


def test_index():
    res = client.get('/', follow_redirects=True)
    assert res.status_code == 200


def test_rating():
    for lang in app.config['SUPPORTED_LANGUAGES']:
        assert client.get(f'/{lang}/rating').status_code == 200
        assert client.get(f'/{lang}/rating?page=2').status_code == 200
        assert client.get(f'/{lang}/rating/MEN?page=2').status_code == 200
        assert client.get(f'/{lang}/rating/WOMEN?page=2').status_code == 200

def test_user_search():
    player =_create_test_player()
    for lang in app.config['SUPPORTED_LANGUAGES']:
        res = client.get(f'/{lang}')
