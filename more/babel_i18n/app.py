# -*- coding: utf-8 -*-
"""
    more.babel_i18n.core
    ~~~~~~~~~~~~~~~~~~~~

    App with Babel support.

    :copyright:
        (c) 2017 by Tobias dpausp
        (c) 2013 by Armin Ronacher, Daniel Neuhäuser and contributors.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
from babel import Locale
import morepath
from more.babel_i18n.domain import Domain
from more.babel_i18n.request_utils import BabelRequestUtils
try:
    from pytz.gae import pytz
except ImportError:
    from pytz import timezone
else:
    timezone = pytz.timezone  # pragma: no cover

from .constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE,\
    DEFAULT_DATE_FORMATS


def find_app_root(app):
    return os.path.dirname(sys.modules[app.__module__].__file__)


class BabelApp(morepath.App):
    """Central controller class that can be used to configure how
    more.babel_i18n behaves.  Each application that wants to use Babel
    has to subclass this. :meth:`babel_init` must be called before using
    Babel methods.
    """

    def babel_init(self):
        """Initializes the more.babel_i18n App.
        """
        cfg = self.settings.babel_i18n
        #: a mapping of Babel datetime format strings that can be modified
        #: to change the defaults.  If you invoke :func:`format_datetime`
        #: and do not provide any format string more.babel_i18n will do the
        #: following things:
        #:
        #: 1.   look up ``date_formats['datetime']``.  By default ``'medium'``
        #:      is returned to enforce medium length datetime formats.
        #: 2.   ``date_formats['datetime.medium'] (if ``'medium'`` was
        #:      returned in step one) is looked up.  If the return value
        #:      is anything but `None` this is used as new format string.
        #:      otherwise the default for that language is used.
        translations_path = cfg.translations_path or os.path.join(find_app_root(self), 'translations')
        domain = Domain(domain=cfg.domain, dirname=translations_path)
        self.babel = BabelI18n(self, domain=domain, date_formats=DEFAULT_DATE_FORMATS.copy())


class BabelI18n:
    def __init__(self, app, domain, date_formats):
        self.app = app
        self.domain = domain
        self.settings = self.app.settings.babel_i18n
        self.date_formats = date_formats
        self.locale_selector_func = None
        self.timezone_selector_func = None
        self.locale_cache = {}

    def localeselector(self, f):
        """Registers a callback function for locale selection.  The default
        behaves as if a function was registered that returns `None` all the
        time.  If `None` is returned, the locale falls back to the one from
        the configuration.

        This has to return the locale as string (eg: ``'de_AT'``, ''`en_US`'')
        """
        self.locale_selector_func = f
        return f

    def timezoneselector(self, f):
        """Registers a callback function for timezone selection.  The default
        behaves as if a function was registered that returns `None` all the
        time.  If `None` is returned, the timezone falls back to the one from
        the configuration.

        This has to return the timezone as string (eg: ``'Europe/Vienna'``)
        """
        self.timezone_selector_func = f
        return f

    def list_translations(self):
        """Returns a list of all the locales translations exist for.  The
        list returned will be filled with actual locale objects and not just
        strings.

        .. versionadded:: 0.6
        """
        return self.domain.list_translations()

    @property
    def default_locale(self):
        """The default locale from the configuration as instance of a
        `babel.Locale` object.
        """
        return self.load_locale(self.settings.default_locale)

    @property
    def default_timezone(self):
        """The default timezone from the configuration as instance of a
        `pytz.timezone` object.
        """
        return timezone(self.settings.default_timezone)

    def load_locale(self, locale):
        """Load locale by name and cache it. Returns instance of a
        `babel.Locale` object.
        """
        rv = self.locale_cache.get(locale)
        if rv is None:
            self.locale_cache[locale] = rv = Locale.parse(locale)
        return rv

    def __repr__(self):
        return '<BabelI18n({}, {})>'.format(self.babel, self.domain)


@BabelApp.setting_section(section="babel_i18n")
def babel_i18n_settings():
    return {
        'default_locale': DEFAULT_LOCALE,
        'translations_path': None,
        'default_timezone': DEFAULT_TIMEZONE,
        'configure_jinja': True,
        'domain': 'messages'
    }


@BabelApp.tween_factory()
def babel_tween_factory(app, handler):
    def babel_tween(request):
        request.i18n = BabelRequestUtils(request)
        return handler(request)

    return babel_tween
