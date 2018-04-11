from app import app, load_modules

load_modules()

if __name__ == '__main__':
    app.run(port=10000, host='0.0.0.0')
