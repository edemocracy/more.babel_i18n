# -*- coding: utf-8 -*-
"""
    more.babel_i18n
    ~~~~~~~~~~~~~~~

    Implements i18n/l10n support for Morepath applications based on Babel.

    :copyright:
        (c) 2017 Tobias dpausp
        (c) 2013 by Serge S. Koval, Armin Ronacher and contributors.
    :license: BSD, see LICENSE.BSD for more details.
"""
from __future__ import absolute_import

from .app import BabelApp


__all__ = (
    'BabelApp', 'BabelRequest'
)
