import os
import pdorclient
import pdorclient.errors
import re

# http://tools.ietf.org/html/rfc2606
# http://www.iana.org/domains/example/

TEST_DATA_NOTES = r'pdorclient unit testing !@#$%^&*()_'
TEST_DATA_SOA = ' '.join([
  'ns1.pdorclient.test',         # primary_ns
  'hostmaster.pdorclient.test',  # contact
  '007',                         # serial
  '1200',                        # refresh
  '180',                         # retry
  '1209600',                     # expire
  '10800',                       # minimum
])
TEST_DATA_ZONE = 'pdorclient.test'

CONFIG = pdorclient.Config.CONFIG
TMP_CONFIG = CONFIG + '~'

def setup():
    notes_stripped = re.sub(r'[\w\.\-]', '', TEST_DATA_NOTES)
    if len(notes_stripped) == 0: # pragma: no cover
        assert False, \
          'TEST_DATA_NOTES is too boring.  Add funky characters to ' \
          'potentially expose bugs in the encoding routines.'

# Exercise the code that passes the ``Config`` instance up through the 
# resource stack.  Any code path (dectorate tests with ``@with_setup( 
# tests.disappear_config, tests.restore_config)`` that fails to do this 
# will trigger ``MissingConfigurationError``.
def disappear_config():
    os.rename(CONFIG, TMP_CONFIG)
def restore_config():
    os.rename(TMP_CONFIG, CONFIG)

def blank_slate():
    try:
        pdorclient.Zone.lookup_id(TEST_DATA_ZONE)
    except pdorclient.errors.NameNotFoundError:
        pass
    else: # pragma: no cover
        assert False, \
          '%s should not already exist.  Perhaps it was left over ' \
          'from an old test run?' % TEST_DATA_ZONE

def nuke_zone():
    try:
        zone = pdorclient.Zone.lookup(TEST_DATA_ZONE)
        zone.delete()
    except pdorclient.errors.NameNotFoundError:
        pass
