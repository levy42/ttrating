import datetime
from services import rating_update
import models as m
from app import app


def task(f):
    def wrapper():
        with app.app_context():
            f()

    return wrapper


@task
def update_ua_rating():
    rating_update.update_ua()


@task
def update_world_rating():
    rating_update.update_world()


@task
def delete_expired_users():
    app.logger.info('Running task "delete_expired_users"')
    expired_time = datetime.datetime.now() - datetime.timedelta(days=1)
    m.User.query.filter_by(m.User.registered_on <= expired_time,
                           m.User.confirmed is not True).delete()


@task
def test():
    app.logger.info('Test')
