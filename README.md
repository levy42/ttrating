# [ttennis.life ](ttennis.life)
![GitHub Logo](https://github.com/vitaliylevitskiand/ttrating/blob/master/static/img/logo.png?raw=true)

### Альтернатива існуючому ресурсу <http://reiting.com.ua>

 - install python >= 3.6
 - virtualenv --python={python_path} {venv_path}/ttrating
 - source {venv_path}/ttrating/big/activate
 - pip install -r requirements.txt
 - configure config.py
 - export FLASK_APP=app.py
 - flask db upgrade
 - flask run
---
### To deploy:
>$ flask deploy --migrate/--no-migrate --branch={branch}

Рейтинги беруться з reiting.com.ua