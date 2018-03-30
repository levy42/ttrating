import datetime
from services import rating_update
import models as m
from app import app, cron


def task(f):
    def wrapper():
        with app.app_context():
            f()

    return wrapper


@task
def update_ua_rating():
    rating_update.update_ua()
    rating_update.send_ua_monthly_report()


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
    # rating_update.send_ua_monthly_report()
    app.logger.info('Test')

