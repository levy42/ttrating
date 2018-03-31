from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from models import *


class IndexModelView(ModelView):
    def __init__(self, model, session, *args, **kwargs):
        super(IndexModelView, self).__init__(model, session, *args, **kwargs)
        self.static_folder = 'static'
        self.endpoint = 'admin'
        self.name = 'Player'


class CityView(ModelView):
    column_searchable_list = ('name',)
    column_display_pk = True
    form_columns = ('name', 'weight')


class PlayerView(IndexModelView):
    column_searchable_list = ('name',)
    column_display_pk = True
    form_excluded_columns = ('tournaments', 'external_id')


class TournamentView(ModelView):
    column_searchable_list = ('name',)
    column_display_pk = True
    form_excluded_columns = ('players_info',)


class TranslationView(ModelView):
    column_display_pk = True
    column_searchable_list = ('translated', 'id')


index = PlayerView(Player, db.session, url='/admin')
admin = Admin(name='ttennis.file admin', template_mode='bootstrap3',
              index_view=index)

admin.add_view(TournamentView(Tournament, db.session))
admin.add_view(ModelView(RatingList, db.session))
admin.add_view(CityView(City, db.session))
admin.add_view(ModelView(TopicIssue, db.session))
admin.add_view(ModelView(Topic, db.session))
admin.add_view(ModelView(Translation, db.session))
