from flask import current_app as app
import datetime
from flask import request, render_template, abort, Blueprint
from app import mail, db
import models as m
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer
import config

bp = Blueprint('subscribe', __name__)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


@bp.route('/subscribe/', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'GET':
        return render_template('subscribe.html')
    else:
        password = request.form.get('password')
        player_id = request.form.get('player_id')
        email = request.form.get('email')
        language = request.form.get('lang')
        user = m.User(email, password, confirmed=False, player_id=player_id,
                      confirmed_on=datetime.datetime.now(), language=language)
        token = generate_confirmation_token(email)
        msg = Message(subject=f'Subscribe {config.APP_NAME}',
                      html=render_template('email/subscribe_confirm.html',
                                           token=token, user=user),
                      recipients=[email])
        mail.send(msg)
        db.session.add(user)
        db.session.commit()
        return render_template('subscribe.html', accepted=True)


@bp.route('/subscribe/confirm/<token>')
def confirm(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=24 * 3600
        )
        user = m.User.query.filter_by(email=email).first_or_404()
        user.confirmed = True
        user.confirmed_on = datetime.datetime.now()
        db.session.add(user)
        db.session.commit()
        return render_template('subscribe.html', confirmed=True)

    except Exception as e:
        app.logger.error(f'Failed to confirm email. Reason: {e}')
        raise e


@bp.route('/unsubscribe/<token>')
def unsubscribe(token):
    s = URLSafeSerializer(app.secret_key, salt='unsubscribe')

    try:
        email = s.loads(token)
        m.User.query.filter_by(email=email).delete()
        return _("Ви відписались від оновлень")
    except Exception as e:
        app.logger.error(f'Failed to get email on unsubscibe. Reason: {e}')
        abort(404)
