import datetime
from services import parser, translator, rating_update
import models
from models import db
from app import app

with app.app_context():
    db.create_all()


def test_translate():
    some_name = 'Левицкий Виталий'
    expected = 'Левицький Віталій'

    translated = translator._translate(some_name, 'uk')

    assert expected == translated


def test_parse_rating():
    """This should not fail, but data should be also checked manually"""
    with app.app_context():
        now = datetime.datetime.now()
        year, month = now.year, now.month
        parser.parse_ua(month, year)
        some_player = models.Player.query.order_by('position').first()
        rating = models.Rating.query.filter_by(
            player_id=some_player.id, month=month, year=year)

        assert rating is not None
        assert some_player.rating is not None
        assert rating.rating == some_player.rating


def test_new_rating_report():
    """This should send email on 'TEST_USER_EMAIL', check it manually"""
    with app.app_context():
        user = models.User.query.filter_by(
            email=app.config['TEST_USER_EMAIL']).first()
        if not user:
            user = models.User(email=app.config['TEST_USER_EMAIL'],
                               confirmed=True, password='test', language='uk')
            db.session.add(user)
            db.session.commit()

        rating_update.send_ua_monthly_report()

