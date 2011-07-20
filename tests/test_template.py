from nose.tools import raises, with_setup
import datetime
import logging
import pdorclient
import pdorclient.errors
import tests

# Template instantiation is not tested here.  See test_zone.py.

logger = logging.getLogger(__name__)

def setup():
    tests.disappear_config()

def teardown():
    tests.restore_config()

@raises(pdorclient.errors.MissingConfigurationError)
def test_lookup_with_null_config():
    zone = pdorclient.Template.lookup('example.com')

def test_lookup_seeded():
    template = pdorclient.Template.lookup('East Coast Data Center',
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert isinstance(template, pdorclient.Template)
    assert isinstance(template._id, str) # Internal representation
    assert isinstance(template.id, int)  # External
    assert template.id == 1
    assert isinstance(template.name, str)
    assert template.name == 'East Coast Data Center'
    assert isinstance(template.created_at, datetime.datetime)
    assert isinstance(template.updated_at, datetime.datetime)
    assert template.updated_at >= template.created_at
    assert isinstance(template.ttl, int)

@raises(pdorclient.errors.NameNotFoundError)
def test_raise_not_found_on_missing_template_lookup():
    pdorclient.Template.lookup('Derp',
      config=pdorclient.Config(path=tests.TMP_CONFIG))

@raises(pdorclient.errors.NameNotFoundError)
def test_raise_not_found_on_missing_template_add():
    pdorclient.Zone.from_template(name=tests.TEST_DATA_ZONE,
      template='Derp',
      type=pdorclient.Zone.TYPE_MASTER,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

@raises(pdorclient.errors.Rfc952ViolationError)
def test_raise_rfc952_violation_on_nonsense_name():
    pdorclient.Zone.from_template('example!com',
      template='East Coast Data Center',
      type=pdorclient.Zone.TYPE_MASTER,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

@raises(NotImplementedError)
def test_add_empty_template():
    # This operation is currently not supported.

    template = pdorclient.Template('New template', ttl=3600,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert isinstance(template, pdorclient.Template)
    assert template.id == None
    assert isinstance(template.name, str)
    assert template.name == 'New template'
    assert isinstance(template.ttl, int)
    assert template.ttl == 3600
    assert template.created_at == None
    assert template.updated_at == None

    template.save()
