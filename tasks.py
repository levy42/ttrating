import datetime
from flask_apscheduler import APScheduler
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
    expired_time = datetime.datetime.now() - datetime.timedelta(days=1)
    m.User.query.filter_by(m.User.registered_on <= expired_time).delete()


@task
def test():
    rating_update.send_ua_monthly_report()


cron = APScheduler(app=app)

if __name__ == '__main__':
    cron.start()
