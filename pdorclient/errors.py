import pdorclient

class PdorClientError(Exception):
    def __repr__(self):
        return '%s.%s()' % (self.__module__, self.__class__.__name__)

    def __str__(self):
        return self.__repr__()

class PdorClientLocalError(PdorClientError):
    pass

class InsecureConfigurationError(PdorClientLocalError):
    def __str__(self):
        return 'Hint: chmod o-rw %s' % pdorclient.Config.GLOBAL_CONFIG

class IpV4ParseError(PdorClientLocalError):
    def __init__(self, ipv4):
        self.ipv4 = ipv4

    def __repr__(self):
        return '%s.%s(ipv4=%r)' % (
          self.__module__, self.__class__.__name__, self.ipv4)

class MissingConfigurationError(PdorClientLocalError):
    pass

class PrematurePersistError(PdorClientLocalError):
    def __str__(self):
        return 'Cannot persist without path'

class ReadOnlyAttributeError(PdorClientLocalError):
    def __init__(self, attr):
        self.attr = attr

    def __repr__(self):
        return '%s.%s(attr=%r)' % (
          self.__module__, self.__class__.__name__, self.attr)

class Rfc952ViolationError(PdorClientLocalError):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%s.%s(name=%r)' % (
          self.__module__, self.__class__.__name__, self.name)

class PdorClientRemoteError(PdorClientError):
    pass

class NameNotFoundError(PdorClientRemoteError):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%s.%s(name=%r)' % (
          self.__module__, self.__class__.__name__, self.name)
