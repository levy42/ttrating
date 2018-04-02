from flask import current_app as app
import datetime
from flask import request, render_template, abort, Blueprint, redirect, url_for
from app import mail, db
import models as m
from flask_mail import Message
from flask_babel import _
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer
import config

bp = Blueprint('subscribe', __name__)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


@bp.route('/subscribe/', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'GET':
        accepted = request.args.get('accepted')
        return render_template('subscribe.html', accepted=accepted == 'True',
                               errors={})
    else:
        password = request.form.get('password')
        player_id = request.form.get('player_id')
        email = request.form.get('email')
        language = request.form.get('lang')
        errors = {}
        # validate
        if m.User.query.filter_by(email=email).first():
            errors['email'] = 'Такий email вже зареєстровано!'
        if len(password) < 6:
            errors['password'] = 'Пароль занадто короткий, мінімум 6 символів'

        if errors:
            return render_template('subscribe.html', errors=errors)

        user = m.User(email, password, confirmed=False, player_id=player_id,
                      confirmed_on=datetime.datetime.now(), language=language)
        token = generate_confirmation_token(email)
        db.session.add(user)
        db.session.commit()
        msg = Message(subject=f'Subscribe {config.APP_NAME}',
                      html=render_template('email/subscribe_confirm.html',
                                           token=token, user=user),
                      recipients=[email])
        mail.send(msg)
        return redirect(url_for('.subscribe', accepted=True))


@bp.route('/subscribe/confirm/<token>')
def confirm(token):
    if request.args.get('confirmed'):
        render_template('subscribe.html', confirmed=True)
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
        return redirect(url_for('.subscribe', confirmed=True))

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
