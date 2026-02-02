import sys
# sys.path.insert(0, '.../')
# sys.path.insert(0, '.../app/')

from web_app import app as application, get_locale as app_get_locale
from flask_babel import Babel

babel = Babel(application)

def get_locale():
    return app_get_locale()


if __name__ == "__main__":
    babel.init_app(application, locale_selector=get_locale)
    application.run(port=7343, host='0.0.0.0',
                    debug=True, use_reloader=False)
