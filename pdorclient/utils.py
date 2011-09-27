import logging
import lxml.objectify
import pdorclient.errors
import re

logger = logging.getLogger(__name__)

def is_ipv4(ipv4):
    """Return ``True`` if ``ipv4`` is a valid IPv4 address; ``False``
    otherwise.

    Decimal dotted-quad notation only.

    """
    re_ipv4 = re.compile(
      '^(?:'
        '(?:'
          '25[0-5]|'
          '2[0-4][0-9]|'
          '[01]?[0-9][0-9]?'
        ')\.'
      '){3}'
      '(?:'
        '25[0-5]|'
        '2[0-4][0-9]|'
        '[01]?[0-9][0-9]?'
      ')$')
    if re_ipv4.match(ipv4) is not None:
        return True
    return False

def rfc952ify(name):
    """Return a normalised, RFC-952-compliant version of ``name``.

    May raise ``Rfc952ViolationError``.

    """
    # Silently normalise case and trailing periods.
    normalised = str(name).lower().rstrip('.')

    # See RFC-952 and RFC-1123. 
    # Underscores (_) permitted in RFC-2782.
    re_validity = re.compile(
      '^('
        '\*\.'
      ')?'
      '('
        '(_)?'
        '('
          '[a-z0-9]|'
          '[a-z0-9][a-z0-9\-]*[a-z0-9]'
        ')\.'
      ')*('
        '[a-z0-9]|'
        '[a-z0-9][a-z0-9\-]*[a-z0-9]'
      ')$', re.I)
    m = re_validity.match(normalised)
    if not m:
        raise pdorclient.errors.Rfc952ViolationError(normalised)
    return normalised

def xmlobjify(xml):
    """Return a lxml object representation of ``xml``."""
    if isinstance(xml, unicode):
        xml = xml.encode('ascii')
    if isinstance(xml, lxml.objectify.ObjectifiedElement):
        xmlobj = xml
    else:
        xmlobj = lxml.objectify.fromstring(xml)
    return xmlobj
