import os

from app import create_app

# Yerelde 'development', Render'da APP_ENV=production
app = create_app(os.environ.get('APP_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5110, debug=app.config['DEBUG'])
