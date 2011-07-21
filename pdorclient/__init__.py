import ConfigParser
import datetime
import logging
import os
import pdorclient.errors
import pdorclient.utils
import restclient
import simplejson
import stat
import time
import urllib

# Our version.
__version__ = '0.4.4'

# Git SHA-1 of the PDOR release this release was tested against.
__pdor_compat__ = 'b26990cc5e1cca7782eda512128fa7994395323b'

logger = logging.getLogger(__name__)

class Config(object):
    """Stores client configuration."""
    CONFIG = 'pdorclient.conf'
    GLOBAL_CONFIG = os.path.join('/', 'etc', CONFIG)

    def __getattr__(self, name):
        if name in ('credentials', 'url'):
            return eval('self._%s()' % name)
        raise AttributeError()

    def __init__(self, path=None):
        """Load ``pdorclient.conf``.

        Will raise ``MissingConfigurationError`` if no configuration
        could be found.

        Will raise ``InsecureConfigurationError`` if the credentials in
        your configuration can be read or written to by all users on the
        system.

        """
        self.config = ConfigParser.ConfigParser()

        paths = [self.CONFIG, self.GLOBAL_CONFIG]
        if isinstance(path, str):
            paths.insert(0, path)
        for p in paths:
            try:
                self.config.readfp(open(p))
            except IOError, e:
                if e.errno == 2:
                    continue
            logging.debug('Found configuration at p=%r' % p)
            if os.stat(p)[stat.ST_MODE] & \
              (stat.S_IROTH | stat.S_IWOTH): # pragma: no cover
                raise pdorclient.errors.InsecureConfigurationError()
            self.path = p
            break
        else:
            raise pdorclient.errors.MissingConfigurationError()

    def __repr__(self):
        return '%s.%s(path=%r)' % (
          self.__module__, self.__class__.__name__, self.path)

    def _credentials(self):
        """Return a ``(username, password)`` tuple as read from
        ``/etc/pdorclient.conf``.

        """
        return (self.config.get('client', 'username'),
          self.config.get('client', 'password'),)

    def _url(self):
        """Return the server's URL as read from
        ``/etc/pdorclient.conf``.

        """
        return self.config.get('client', 'url').rstrip('/')

class Resource(object):
    ATTRS = {
      # Attribute : Converter in | Converter out | Default | Emit?
      # '...':    ( ...          , ...           , ...     , ...  ),
      # '...':    ( ...          , ...           , ...     , ...  ),
      #
      # Converters will interpolate at `#'.
    }

    ENCODED_DATE_FMT = '%Y-%m-%dT%H:%M:%SZ'

    STATE_AT_REST = 0
    STATE_DELETED = 1
    STATE_DIRTY   = 2
    STATE_NEW     = 3

    class RestClient(object):
        def __init__(self, config):
            assert isinstance(config, Config)
            self.config = config
            self.rc = restclient.RestClient()
            self.rc.transport.add_credentials(*self.config.credentials)

        def __getattr__(self, name):
            return getattr(self.rc, name) # pragma: no cover

        def __repr__(self):
            return '%s.%s(config=%r)' % (
              self.__module__, self.__class__.__name__, self.config)

        def __setattr__(self, name, value):
            if name in self.__dict__.keys() + ['config', 'rc']:
                object.__setattr__(self, name, value)
            else: # pragma: no cover
                self.rc.name = value

        def delete(self, path, *args, **kwargs):
            logging.debug('HTTP DELETE: %r' % path)
            return self.rc.delete('%s%s' % (self.config.url, path),
              *args, **kwargs)

        def post(self, path, *args, **kwargs):
            logging.debug('HTTP POST: %r' % path)
            return self.rc.post('%s%s' % (self.config.url, path),
              *args, **kwargs)

        def put(self, path, *args, **kwargs):
            logging.debug('HTTP PUT: %r' % path)
            return self.rc.put('%s%s' % (self.config.url, path),
              *args, **kwargs)

    def __getattr__(self, name):

        # External indentifier representation should probably be ints.
        if name == 'id':
            if self._id is not None:
                return int(self._id)
            else:
                return None
        if 'id' in name.split('_'):
            if self._repr[name] is not None:
                return int(self._repr[name])
            else:
                return None

        if name == 'rtype':
            return self._resolve_type()

        if name in self._repr.keys():
            return self._repr[name]

        raise AttributeError()

    def __init__(self, path=None, id=None, repr=None, ro_attrs=None,
      state=None, dirty_repr=None, qp_hash_base=None, children=None,
      config=None):

        self._enforcing = False

        self._r_type = dict(map(
          lambda y: (getattr(self, y), y.replace('TYPE_', '')),
          filter(lambda x: x.startswith('TYPE_'), dir(self))))

        # Optional, because sub-resources may not know their path at 
        # create time.
        if path is not None:
            self._path = path
        else:
            self._path = None

        # Treat all identifiers as strings internally.
        if id is not None:
            self._id = str(id)
        else:
            self._id = None

        if repr is None:
            self._repr = {}
        else: # pragma: no cover
            self._repr = repr

        if ro_attrs is None:
            self._ro_attrs = []
        else: # pragma: no cover
            self._ro_attrs = ro_attrs

        if state is None:
            if self._id is not None:
                self._state = self.STATE_AT_REST
            else:
                self._state = self.STATE_NEW
        else: # pragma: no cover
            self._state = state

        if dirty_repr is None:
            self._dirty_repr = []
        else: # pragma: no cover
            self._dirty_repr = dirty_repr

        # PDOR takes its query parameters as a list of hash keys like 
        # this::
        #
        #     ?blah[foo]=1&blah[bar]=2
        #
        # ``qp_hash_base`` in the example above would be 'blah'.  Set 
        # ``qp_hash_base`` to ``None`` to use regular query parameters.
        self._qp_hash_base = qp_hash_base

        if isinstance(children, list): # pragma: no cover
            self._children = children
        else:
            self._children = []

        if isinstance(config, Config):
            self._config = config
        else:
            self._config = Config()

        if self._state == self.STATE_NEW:
            # New objects can not know what their identities will be 
            # until they are persisted.
            assert self._id == None
        else:
            # All other objects should know their identities.
            assert self._id != None

    def __repr__(self):
        return '%s.%s(path=%r, id=%r, repr=%r, ro_attrs=%r, ' \
          'state=%r, dirty_repr=%r, qp_hash_base=%r, children=%r, ' \
          'config=%r)' % (self.__module__, self.__class__.__name__,
          self._path, self._id, self._repr, self._ro_attrs, self._state,
          self._dirty_repr, self._qp_hash_base, self._children,
          self._config)

    def __setattr__(self, name, value):
        if name in self.__dict__.keys() or name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            if self._enforcing:
                if name in self._ro_attrs or name == 'id':
                    raise pdorclient.errors.ReadOnlyAttributeError(name)

            self._repr[name] = value

            if self._enforcing:
                if name not in self._dirty_repr:
                    self._dirty_repr.append(name)
                object.__setattr__(self, '_state', self.STATE_DIRTY)

    def _create(self):
        rc = Resource.RestClient(self._config)
        qp = self._parameterise()
        response = rc.post('%s?%s' % (self._path, '&'.join(qp)),
          headers={'Accept': 'application/xml'})
        return response

    def _delete(self):
        rc = Resource.RestClient(self._config)
        response = rc.delete('%s/%s' % (self._path, self._id),
          headers={'Accept': 'application/xml'})
        return response

    def _parameterise(self):
        if self._state == self.STATE_NEW:
            attrs = self._repr
        else:
            attrs = self._dirty_repr

        qp = []
        for attr_kw in attrs:
            attr = attr_kw.replace('_', '-')
            (conv_in, conv_out, default, emit) = self.ATTRS[attr]

            if emit is not True:
                continue
            if self._repr[attr_kw] is None:
                continue

            typed_value = self._repr[attr_kw]
            interp = conv_out.replace('#', 'typed_value')
            raw_value = eval(interp)

            if self._qp_hash_base is not None:
                qp.append('%s[%s]=%s' %
                  (str(self._qp_hash_base), attr_kw, raw_value))
            else: # pragma: no cover
                qp.append('%s=%s' % (attr_kw, raw_value))

        return qp

    def _refresh(self, xml):
        if xml is None:
            return # _create/_save was a no-op

        xmlobj = pdorclient.utils.xmlobjify(xml)

        attrs = {}
        for attr in self.ATTRS.keys():
            attr_kw = attr.replace('-', '_')
            (conv_in, conv_out, default, emit) = self.ATTRS[attr]

            if attr in ('id',):
                attr_kw = '_%s' % attr
            elif attr_kw not in self._ro_attrs:
                continue

            raw_value = getattr(xmlobj, attr, None)
            if raw_value == '':
                raw_value = default

            if raw_value != None:
                interp = conv_in.replace('#', "'%s'" % raw_value)
                typed_value = eval(interp)
            else:
                typed_value = None

            logging.debug('%s._refresh() found %r=%r' %
              (self.__class__.__name__, attr_kw, typed_value))
            attrs[attr_kw] = typed_value

        self._enforcing = False
        for attr_kw in attrs.keys():
            setattr(self, attr_kw, attrs[attr_kw])
        self._enforcing = True

    def _resolve_type(self):
        """Return a pretty-printed, humanised representation of this
        resource's type."""
        return self._r_type[self.type]

    def _save(self):
        rc = Resource.RestClient(self._config)
        qp = self._parameterise()
        response = rc.put('%s/%s?%s' % (self._path, self._id,
          '&'.join(qp)), headers={'Accept': 'application/xml'})
        return response

    def delete(self):
        for c in self._children:
            logging.debug('Deleting child: %r' % c)
            c.delete()

        response = self._delete()
        logging.debug('Response from remote: %r' % response)
        self._id = None
        self._state = self.STATE_DELETED

    def save(self):
        if self._path is None:
            raise pdorclient.errors.PrematurePersistError()

        response = None
        if self._state == self.STATE_NEW:
            response = self._create()
        elif self._state == self.STATE_DIRTY:
            response = self._save()
        logging.debug('Response from remote: %r' % response)

        self._refresh(response)

        for c in self._children:
            logging.debug('Persisting child: %r' % c)
            c.save()

        self._state = self.STATE_AT_REST

    @classmethod
    def from_xml(klass, xml, config=None):
        xmlobj = pdorclient.utils.xmlobjify(xml)

        attrs = {}
        for attr in klass.ATTRS.keys():
            attr_kw = attr.replace('-', '_')
            (conv_in, conv_out, default, emit) = klass.ATTRS[attr]

            if attr in xmlobj.attrib.keys():
                raw_value = xmlobj.attrib[attr]
            else:
                raw_value = getattr(xmlobj, attr, None)
            if raw_value == '':
                raw_value = default

            if raw_value != None:
                interp = conv_in.replace('#', "'%s'" % raw_value)
                typed_value = eval(interp)
            else:
                continue

            logging.debug('%s.from_xml() found %r=%r' %
              (klass.__name__, attr_kw, typed_value))
            attrs[attr_kw] = typed_value

        attrs['config'] = config

        return klass(**attrs)

class Record(Resource):
    # http://wiki.powerdns.com/trac/wiki/fields
    # http://doc.powerdns.com/types.html

    ATTRS = {
      'change-date': ( 'int(#)', 'str(#)',          None, True),
      'content':     ( '#',      'urllib.quote(#)', None, True),
      'created-at':  (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Record.ENCODED_DATE_FMT)',
        None,
        False
      ),
      'domain-id':   ( '#',      'urllib.quote(#)', None, False),
      'id':          ( '#',      'urllib.quote(#)', None, True),
      'name':        ( '#',      'urllib.quote(#)', None, True),
      'prio':        ( 'int(#)', 'str(#)',          0,    True),
      'ttl':         ( 'int(#)', 'str(#)',          None, True),
      'type':        (
        "eval('Record.TYPE_%s' % str(#).upper())",
        "dict(map(lambda y: (getattr(Record, y), "
          "y.replace('TYPE_', '')), "
          "filter(lambda x: x.startswith('TYPE_'), dir(Record))))[#]",
        None,
        True
      ),
      'updated-at':  (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Record.ENCODED_DATE_FMT)',
        None,
        False
      ),
    }

    TYPE_A      =  0
    TYPE_AAAA   =  1
    TYPE_AFSDB  =  2                             # Not supported by PDOR
    TYPE_CERT   =  3                             # Not supported
    TYPE_CNAME  =  4
    TYPE_DNSKEY =  5                             # Not supported
    TYPE_DS     =  6                             # Not supported
    TYPE_HINFO  =  7                             # Not supported
    TYPE_KEY    =  8                             # Not supported
    TYPE_LOC    =  9
    TYPE_MX     = 10
    TYPE_NAPTR  = 11                             # Not supported
    TYPE_NS     = 12
    TYPE_NSEC   = 13                             # Not supported
    TYPE_PTR    = 14
    TYPE_RP     = 15                             # Not supported
    TYPE_RRSIG  = 16                             # Not supported
    TYPE_SOA    = 17
    TYPE_SPF    = 18
    TYPE_SSHFP  = 19                             # Not supported
    TYPE_SRV    = 20
    TYPE_TXT    = 21

    def __cmp__(self, other):
        type_cmp = cmp(self.type, other.type)
        if type_cmp != 0:
            return type_cmp
        return cmp(self.name, other.name)

    def __init__(self, name, type, content, ttl=None, id=None,
      domain_id=None, prio=None, change_date=None, created_at=None,
      updated_at=None, config=None):

        # The following attributes are core PowerDNS attributes.  The 
        # ``pdns`` nameserver daemon requires them to function.

        assert type in map(lambda y: getattr(Record, y),
          filter(lambda x: x.startswith('TYPE_'), dir(Record)))
        assert isinstance(content, str)

        # Record TTLs are normally mandatory.  PowerDNS on Rails adds a 
        # TTL field at the zone layer that it will apply to records if 
        # no TTL is supplied with a new record.
        if ttl is not None:
            assert isinstance(ttl, int)

        if domain_id is not None:
            assert isinstance(domain_id, int) or \
              isinstance(domain_id, str)
        if prio is not None:
            assert isinstance(prio, int)
        if change_date is not None:
            assert isinstance(change_date, int)

        # The following attributes are PowerDNS on Rails extensions.  
        # The ``pdns`` nameserver daemon does not look at these 
        # attributes.

        if created_at is not None:
            assert isinstance(created_at, datetime.datetime)
        if updated_at is not None:
            assert isinstance(updated_at, datetime.datetime)

        if domain_id is not None:
            Resource.__init__(self,
              path='/domains/%s/records' % str(domain_id),
              id=id, qp_hash_base='record', config=config)
            self.domain_id = str(domain_id)
        else:
            Resource.__init__(self, path=None, id=id,
              qp_hash_base='record', config=config)
            self.domain_id = None

        self.change_date = change_date
        self.content = content
        self.created_at = created_at
        self.name = pdorclient.utils.rfc952ify(name)
        self.prio = prio
        self.ttl = ttl
        self.type = type
        self.updated_at = updated_at

        self._ro_attrs.append('created_at')
        self._ro_attrs.append('domain_id')
        self._ro_attrs.append('updated_at')

        self._enforcing = True

class Template(Resource):
    ATTRS = {
      'created-at':  (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Record.ENCODED_DATE_FMT)',
        None,
        False
      ),
      'id':          ( '#',      'urllib.quote(#)', None, True),
      'name':        ( '#',      'urllib.quote(#)', None, True),
      'ttl':         ( 'int(#)', 'str(#)',          None, True),
      'updated-at':  (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Record.ENCODED_DATE_FMT)',
        None,
        False
      ),
    }

    def __cmp__(self, other): # pragma: no cover
        return cmp(self.name, other.name)

    def __init__(self, name, ttl, id=None, created_at=None,
      updated_at=None, config=None):

        assert isinstance(ttl, int)
        if created_at is not None:
            assert isinstance(created_at, datetime.datetime)
        if updated_at is not None:
            assert isinstance(updated_at, datetime.datetime)

        Resource.__init__(self, path='/zone_templates', id=id,
          qp_hash_base='template', config=config)

        self.created_at = created_at
        self.name = str(name)
        self.ttl = ttl
        self.updated_at = updated_at

        self._ro_attrs.append('created_at')
        self._ro_attrs.append('updated_at')

        self._enforcing = True

    def _create(self): # pragma: no cover
        # Scratching my own itch here -- I do not need to modify 
        # templates autonomously.
        raise NotImplementedError()

    def _delete(self): # pragma: no cover
        # Scratching my own itch here -- I do not need to modify 
        # templates autonomously.
        raise NotImplementedError()

    def _save(self): # pragma: no cover
        # Scratching my own itch here -- I do not need to modify 
        # templates autonomously.
        raise NotImplementedError()

    @staticmethod
    def lookup(name, config=None):
        """Lookup and return a ``Template`` object for ``name``.

        ``config``, if supplied, should be an instance of ``Config``.

        Will raise ``NameNotFoundError`` if an exact match on ``name``
        does not exist.

        """
        if not isinstance(config, Config):
            config = Config()

        rc = restclient.RestClient()
        rc.transport.add_credentials(*config.credentials)

        response = rc.get('%s/zone_templates' % config.url,
          headers={'Accept': 'application/xml'})
        xmlobj = pdorclient.utils.xmlobjify(response)

        for t in xmlobj.iterchildren():
            template = Template.from_xml(t, config)
            if template.name == name:
                return template

        raise pdorclient.errors.NameNotFoundError(name)

class Zone(Resource):
    # http://wiki.powerdns.com/trac/wiki/fields

    ATTRS = {
      'account':         ( '#',      '#',               None, False),
      'created-at':      (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Zone.ENCODED_DATE_FMT)',
        None,
        False
      ),
      'id':              ( '#',      'urllib.quote(#)', None, True),
      'last-check':      ( 'int(#)', 'str(#)',          None, True),
      'master':          (
        "#.split(',')",
        "urllib.quote(','.join(#))",
        None,
        True
      ),
      'name':            ( '#',      'urllib.quote(#)', None, True),
      'notes':           ( '#',      'urllib.quote(#)', None, True),
      'notified-serial': ( 'int(#)', 'str(#)',          None, True),
      'ttl':             ( 'int(#)', 'str(#)',          None, True),
      'type':            (
        "eval('Zone.TYPE_%s' % str(#).upper())",
        "dict(map(lambda y: (getattr(Zone, y), "
          "y.replace('TYPE_', '')), "
          "filter(lambda x: x.startswith('TYPE_'), dir(Zone))))[#]",
        None,
        True
       ),
      'updated-at':      (
        'datetime.datetime('
          '*(time.strptime(#, Record.ENCODED_DATE_FMT)[0:6]))',
        '#.strftime(Zone.ENCODED_DATE_FMT)',
        None,
        False
      ),
      'zone-template-name': ( '#', 'urllib.quote(#)', None, True),
    }

    TYPE_NATIVE     = 0
    TYPE_MASTER     = 1
    TYPE_SLAVE      = 2
    TYPE_SUPERSLAVE = 3                          # Not supported by PDOR

    def __getattr__(self, name):
        if name == 'records':
            return self._children
        return Resource.__getattr__(self, name)

    def __init__(self, name, type, master=None, last_check=None,
      id=None, notified_serial=None, account=None, created_at=None,
      updated_at=None, notes=None, ttl=None, template=None,
      config=None):

        # The following attributes are core PowerDNS attributes.  The 
        # ``pdns`` nameserver daemon requires them to function.

        assert type in map(lambda y: getattr(Zone, y),
          filter(lambda x: x.startswith('TYPE_'), dir(Zone)))
        if isinstance(master, str):
            master = master.split(',')
        if master is not None:
            assert isinstance(master, list)
            master = filter(lambda x: len(x) > 0, master)
            if len(master) == 0:
                master = None
            else:
                for ipv4 in master:
                    if not pdorclient.utils.is_ipv4(ipv4):
                        raise pdorclient.errors.IpV4ParseError(ipv4)
        if last_check is not None: # pragma: no cover
            assert isinstance(last_check, int)
        if notified_serial is not None: # pragma: no cover
            assert isinstance(notified_serial, int)
        if account is not None: # pragma: no cover
            assert isinstance(account, str)

        # The following attributes are PowerDNS on Rails extensions.  
        # The ``pdns`` nameserver daemon does not look at these 
        # attributes.

        if created_at is not None:
            assert isinstance(created_at, datetime.datetime)
        if updated_at is not None:
            assert isinstance(updated_at, datetime.datetime)
        if notes is not None:
            assert isinstance(notes, str)
        if ttl is not None:
            assert isinstance(ttl, int)
        if template is not None:
            assert isinstance(template, str)

        Resource.__init__(self, path='/domains', id=id,
          qp_hash_base='domain', config=config)

        self.account = account
        self.created_at = created_at
        self.last_check = last_check
        self.master = master
        self.name = pdorclient.utils.rfc952ify(name)
        self.notes = notes
        self.notified_serial = notified_serial
        self.ttl = ttl
        self.type = type
        self.updated_at = updated_at
        self.zone_template_name = template

        self._ro_attrs.append('account')
        self._ro_attrs.append('created_at')
        self._ro_attrs.append('last_check')
        self._ro_attrs.append('notified_serial')
        self._ro_attrs.append('updated_at')
        self._ro_attrs.append('zone_template_name')

        self._enforcing = True

    def __setattr__(self, name, value):
        if name == 'records':
            self._children = value
        else:
            Resource.__setattr__(self, name, value)

    def _refresh(self, xml):
        Resource._refresh(self, xml)

        if xml is not None:
            xmlobj = pdorclient.utils.xmlobjify(xml)

            if hasattr(xmlobj, 'records') and \
              xmlobj.records.countchildren() > 0:
                # This zone has been created from a template.  
                # Instantiate RRs from what the server is telling us we 
                # should have.
                for r in xmlobj.records.iterchildren():
                    r = Record.from_xml(r, self._config)
                    self.records.append(r)

        # Update children's domain-id and resource paths so that 
        # they, too, may be persisted.
        for r in self.records:
            r._enforcing = False
            r._path = '/domains/%s/records' % str(self.id)
            r.domain_id = str(self.id)
            r._enforcing = True

    @staticmethod
    def from_template(name, template, type, config=None):
        """Instantiate and return a new ``Zone`` instance from an
        existing template.

        Will raise ``NameNotFoundError`` if an exact match on
        ``template`` does not exist.

        Will raise ``Rfc952ViolationError`` if ``name`` is nonsense.

        """
        # Zone persists are delayed.  The caller should not have to wait 
        # until persist time to be told the template they specifed does 
        # not exist.  Do a lookup now and raise an immediate exception 
        # if ``template`` is invalid.
        Template.lookup(template, config)

        return Zone(name=name, type=type, template=template,
          config=config)

    @staticmethod
    def lookup(name, match=None, config=None):
        """Lookup and return a ``Zone`` instance for ``name``.

        By default, this method will query for *all* DNS resource
        records (RRs) for a zone and create one ``Record`` instance for
        each RR.  This behaviour can keep Rails busy for a long time if
        the zone contains many thousands of RRs [1]_.  If you are not
        interested in iterating over every single RR in a zone, supply
        a substring to ``match`` to limit the number of RRs returned::

            Zone.lookup('example.com' match='ns')

        Alternatively, supply ``match=False`` to ignore all RRs.  The
        returned ``Zone`` instance will contain no ``Record`` instances.

        ``config``, if supplied, should be an instance of ``Config``.

        Will raise ``NameNotFoundError`` if an exact match on ``name``
        does not exist.

        Will raise ``Rfc952ViolationError`` if ``name`` or ``match`` is
        nonsense.

        .. [1] The delay is an artefact of the server-side
        implementation and cannot be fixed here.

        """
        if not isinstance(config, Config):
            config = Config()

        if isinstance(name, int): # pragma: no cover
            id = name
        else:
            id = Zone.lookup_id(name, config)

        rc = restclient.RestClient()
        rc.transport.add_credentials(*config.credentials)

        # We can either query for all RRs or a subset of RRs.  There is 
        # presently no way to tell PDOR that we do not want any RRs.  
        # For now, query for RRs that are unlikely to exist (to keep 
        # server-side processing down) and discard the results.
        match_normalised = 'faffenblorg'

        if match is not None and not isinstance(match, bool):
            match_normalised = pdorclient.utils.rfc952ify(str(match))
        elif match is None or isinstance(match, bool) and match is True:
            match_normalised = None # Fetch all RRs

        if match_normalised is not None:
            response = rc.get('%s/domains/%d?record=%s' %
              (config.url, id, match_normalised),
              headers={'Accept': 'application/xml'})
        else:
            response = rc.get('%s/domains/%d' % (config.url, id),
              headers={'Accept': 'application/xml'})
        logging.debug('Response from remote: %r' % response)
        xmlobj = pdorclient.utils.xmlobjify(response)

        name = Zone.from_xml(xmlobj, config)

        if not (isinstance(match, bool) and match is False):
            for r in xmlobj.records.iterchildren():
                r = Record.from_xml(r, config)
                name.records.append(r)

        return name

    @staticmethod
    def lookup_id(name, config=None):
        """Return the PDNS-internal domain ID for ``name``.

        ``config``, if supplied, should be an instance of ``Config``.

        Will raise ``NameNotFoundError`` if an exact match on ``name``
        does not exist.

        Will raise ``Rfc952ViolationError`` if ``name`` is nonsense.

        """
        if not isinstance(config, Config):
            config = Config()

        rc = restclient.RestClient()
        rc.transport.add_credentials(*config.credentials)

        # This is the only REST verb in PowerDNS on Rails that spits out 
        # a JSON-encoded response.  The rest of the stuff uses XML.
        response = simplejson.loads(rc.get(
          '%s/search/results?q=%s' %
          (config.url, pdorclient.utils.rfc952ify(name)),
          headers={'Accept': 'application/json'}))
        logging.debug('Response from remote: %r' % response)

        for z in response:
            if z['domain']['name'] == name:
                return int(z['domain']['id'])

        raise pdorclient.errors.NameNotFoundError(name)
