# -*- coding: utf-8 -*-
"""
    more.babel_i18n.request
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyright:
        (c) 2017 by Tobias dpausp
        (c) 2013 by Armin Ronacher, Daniel Neuhäuser and contributors.
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from contextlib import contextmanager
from babel import dates, numbers
import morepath
from more.babel_i18n.speaklater import LazyString
from more.babel_i18n.domain import Domain
try:
    from pytz.gae import pytz
except ImportError:
    from pytz import timezone, UTC
else:  # pragma: no cover
    timezone = pytz.timezone
    UTC = pytz.UTC

class BabelRequestUtils:
    """
    Various helper methods which are bound to the given request.
    """

    def __init__(self, request):
        self.request = request
        self.babel = request.app.babel
        self.locale = None
        self.tzinfo = None
        # XXX: hack, only works for a single thread. We want to share the domain, I think
        self.babel.domain.request = request

    def get_locale(self):
        """Returns the locale that should be used for this request as
        `babel.Locale` object.  This returns `None` if used outside of
        a request.
        """
        locale = self.locale
        # no locale found on current request context
        if self.locale is None:
            if self.babel.locale_selector_func is not None:
                locale = self.babel.load_locale(
                    self.babel.locale_selector_func(self.request)
                )
            else:
                locale = self.babel.default_locale

            self.locale = locale

        return locale

    def get_timezone(self):
        """Returns the timezone that should be used for this request as `pytz.timezone` object.
        """
        tzinfo = self.tzinfo
        if tzinfo is None:
            if self.babel.timezone_selector_func is not None:
                rv = self.babel.timezone_selector_func()
                if rv is None:
                    tzinfo = self.babel.default_timezone
                else:
                    if isinstance(rv, str):
                        tzinfo = timezone(rv)
                    else:
                        tzinfo = rv
            else:
                tzinfo = self.babel.default_timezone

            self.tzinfo = tzinfo

        return tzinfo

    def refresh(self):
        """Refreshes the cached timezones and locale information.  This can
        be used to switch a translation between a request and if you want
        the changes to take place immediately, not just with the next request::

            user.timezone = request.form['timezone']
            user.locale = request.form['locale']
            refresh()
            flash(gettext('Language was changed'))

        Without that refresh, the :func:`~flash` function would probably
        return English text and a now German page.
        """
        self.tzinfo = None
        self.locale = None

    @contextmanager
    def force_locale(self, locale):
        """Temporarily overrides the currently selected locale.
        Sometimes it is useful to switch the current locale to
        different one, do some tasks and then revert back to the
        original one. For example, if the user uses German on the
        web site, but you want to send them an email in English,
        you can use this function as a context manager::

            with force_locale('en_US'):
                send_email(gettext('Hello!'), ...)

        :param locale: The locale to temporary switch to (ex: 'en_US').
        """
        orig_locale_selector_func = self.babel.locale_selector_func
        orig_attrs = {}
        for key in ('translations', 'locale'):
            orig_attrs[key] = getattr(self, key, None)

        try:
            self.babel.locale_selector_func = lambda: locale
            for key in orig_attrs:
                setattr(self, key, None)
            yield
        finally:
            self.babel.locale_selector_func = orig_locale_selector_func
            for key, value in orig_attrs.items():
                setattr(self, key, value)

    def _get_format(self, key, format=None):
        """A small helper for the datetime formatting functions.  Looks up
        format defaults for different kinds.
        """
        if format is None:
            format = self.babel.date_formats[key]
        if format in ('short', 'medium', 'full', 'long'):
            rv = self.babel.date_formats['%s.%s' % (key, format)]
            if rv is not None:
                format = rv
        return format

    def _date_format(self, formatter, obj, format, rebase, **extra):
        """Internal helper that formats the date."""
        locale = self.get_locale()
        extra = {}
        if formatter is not dates.format_date and rebase:
            extra['tzinfo'] = self.get_timezone()
        return formatter(obj, format, locale=locale, **extra)

    def to_user_timezone(self, datetime):
        """Convert a datetime object to the user's timezone.  This automatically
        happens on all date formatting unless rebasing is disabled.  If you need
        to convert a :class:`datetime.datetime` object at any time to the user's
        timezone (as returned by :func:`get_timezone` this function can be used).
        """
        if datetime.tzinfo is None:
            datetime = datetime.replace(tzinfo=UTC)
        tzinfo = self.get_timezone()
        return tzinfo.normalize(datetime.astimezone(tzinfo))

    def to_utc(self, datetime):
        """Convert a datetime object to UTC and drop tzinfo.  This is the
        opposite operation to :func:`to_user_timezone`.
        """
        if datetime.tzinfo is None:
            datetime = self.get_timezone().localize(datetime)
        return datetime.astimezone(UTC).replace(tzinfo=None)

    def format_datetime(self, datetime=None, format=None, rebase=True):
        """Return a date formatted according to the given pattern.  If no
        :class:`~datetime.datetime` object is passed, the current time is
        assumed.  By default rebasing happens which causes the object to
        be converted to the users's timezone (as returned by
        :func:`to_user_timezone`).  This function formats both date and
        time.

        The format parameter can either be ``'short'``, ``'medium'``,
        ``'long'`` or ``'full'`` (in which cause the language's default for
        that setting is used, or the default from the :attr:`Babel.date_formats`
        mapping is used) or a format string as documented by Babel.

        This function is also available in the template context as filter
        named `datetimeformat`.
        """
        format = self._get_format('datetime', format)
        return self._date_format(dates.format_datetime, datetime, format, rebase)

    def format_date(self, date=None, format=None, rebase=True):
        """Return a date formatted according to the given pattern.  If no
        :class:`~datetime.datetime` or :class:`~datetime.date` object is passed,
        the current time is assumed.  By default rebasing happens which causes
        the object to be converted to the users's timezone (as returned by
        :func:`to_user_timezone`).  This function only formats the date part
        of a :class:`~datetime.datetime` object.

        The format parameter can either be ``'short'``, ``'medium'``,
        ``'long'`` or ``'full'`` (in which cause the language's default for
        that setting is used, or the default from the :attr:`Babel.date_formats`
        mapping is used) or a format string as documented by Babel.

        This function is also available in the template context as filter
        named `dateformat`.
        """
        if rebase and isinstance(date, datetime):
            date = self.to_user_timezone(date)
        format = self._get_format('date', format)
        return self._date_format(dates.format_date, date, format, rebase)

    def format_time(self, time=None, format=None, rebase=True):
        """Return a time formatted according to the given pattern.  If no
        :class:`~datetime.datetime` object is passed, the current time is
        assumed.  By default rebasing happens which causes the object to
        be converted to the users's timezone (as returned by
        :func:`to_user_timezone`).  This function formats both date and
        time.

        The format parameter can either be ``'short'``, ``'medium'``,
        ``'long'`` or ``'full'`` (in which cause the language's default for
        that setting is used, or the default from the :attr:`Babel.date_formats`
        mapping is used) or a format string as documented by Babel.

        This function is also available in the template context as filter
        named `timeformat`.
        """
        format = self._get_format('time', format)
        return self._date_format(dates.format_time, time, format, rebase)

    def format_timedelta(self, datetime_or_timedelta, granularity='second',
                         add_direction=False, threshold=0.85):
        """Format the elapsed time from the given date to now or the given
        timedelta.
        This function is also available in the template context as filter
        named `timedeltaformat`.
        """
        if isinstance(datetime_or_timedelta, datetime):
            datetime_or_timedelta = datetime.utcnow() - datetime_or_timedelta
        return dates.format_timedelta(
            datetime_or_timedelta,
            granularity,
            threshold=threshold,
            add_direction=add_direction,
            locale=self.get_locale())

    def format_number(self, number):
        """Return the given number formatted for the locale in request

        :param number: the number to format
        :return: the formatted number
        :rtype: unicode
        """
        locale = self.get_locale()
        return numbers.format_number(number, locale=locale)

    def format_decimal(self, number, format=None):
        """Return the given decimal number formatted for the locale in request

        :param number: the number to format
        :param format: the format to use
        :return: the formatted number
        :rtype: unicode
        """
        locale = self.get_locale()
        return numbers.format_decimal(number, format=format, locale=locale)

    def format_currency(self, number, currency, format=None, currency_digits=True,
                        format_type='standard'):
        """Return the given number formatted for the locale in request
        :param number: the number to format
        :param currency: the currency code
        :param format: the format to use
        :param currency_digits: use the currency’s number of decimal digits
                                [default: True]
        :param format_type: the currency format type to use
                            [default: standard]
        :return: the formatted number
        :rtype: unicode
        """
        locale = self.get_locale()
        return numbers.format_currency(
            number,
            currency,
            format=format,
            locale=locale,
            currency_digits=currency_digits,
            format_type=format_type
        )

    def format_percent(self, number, format=None):
        """Return formatted percent value for the locale in request

        :param number: the number to format
        :param format: the format to use
        :return: the formatted percent number
        :rtype: unicode
        """
        locale = self.get_locale()
        return numbers.format_percent(number, format=format, locale=locale)

    def format_scientific(self, number, format=None):
        """Return value formatted in scientific notation for the locale in request

        :param number: the number to format
        :param format: the format to use
        :return: the formatted percent number
        :rtype: unicode
        """
        locale = self.get_locale()
        return numbers.format_scientific(number, format=format, locale=locale)

    def gettext(self, *args, **kwargs):
        return self.babel.domain.gettext(*args, **kwargs)

    _ = gettext  # noqa

    def ngettext(self, *args, **kwargs):
        return self.babel.domain.ngettext(*args, **kwargs)

    def pgettext(self, *args, **kwargs):
        return self.babel.domain.pgettext(*args, **kwargs)

    def npgettext(self, *args, **kwargs):
        return self.babel.domain.npgettext(*args, **kwargs)

    def lazy_gettext(self, *args, **kwargs):
        return LazyString(self.gettext, *args, **kwargs)

    def lazy_pgettext(self, *args, **kwargs):
        return LazyString(self.pgettext, *args, **kwargs)
