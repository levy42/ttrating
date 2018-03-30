# [ttennis.life ](ttennis.life)
<img src="https://github.com/vitaliylevitskiand/ttrating/blob/master/static/img/logo.png" width="100" height="100">

### Альтернатива ресурсу <http://reiting.com.ua>

1) Install python >= 3.6
2) Setup virtualenv
    ```console
    foo@bar:~$ virtualenv --python={python_path} {venv_path}/ttrating
    foo@bar:~$ source {venv_path}/ttrating/big/activate
    ```
3) install dependencies
    ```console
    foo@bar:~$ pip install -r requirements.txt
    ```

#### Configuration
4) Create `config.cfg` file
5) Override needed configs from config.py (or add new)
    ```console
    foo@bar:~$ export FLASK_APP=app.py
    ```

##### Run
6) Migrate DB
    ```console
    foo@bar:~$ flask db upgrade
    ```
7) Run
	```console
    foo@bar:~$ FLASK_APP=app.py APP_CONFIG=config.cfg flask run
    ```

##### Deployment:
```console
foo@bar:~$ flask deploy --migrate/--no-migrate --branch={branch}
```

Рейтинги беруться з reiting.com.ua