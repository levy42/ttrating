from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from app import app
from models import *

admin = Admin(app, name='ttrating', template_mode='bootstrap3')
admin.add_view(ModelView(Player, db.session))
admin.add_view(ModelView(Tournament, db.session))
admin.add_view(ModelView(Rating, db.session))
admin.add_view(ModelView(RatingList, db.session))
admin.add_view(ModelView(City, db.session))
admin.add_view(ModelView(Game, db.session))
