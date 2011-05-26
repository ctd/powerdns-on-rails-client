from nose.tools import raises, with_setup
import datetime
import logging
import pdorclient
import pdorclient.errors
import tests

# I only bothered to implement basic template lookups so I could 
# instantiate new zones using existing templates.  Template lookups 
# should work, but any attempt to modify and persist a template should 
# fail in an obvious way.  Remove this comment when write support is 
# added.

logger = logging.getLogger(__name__)

@with_setup(tests.disappear_config, tests.restore_config)
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
    pdorclient.Template.lookup('Derp')

@raises(pdorclient.errors.NameNotFoundError)
@with_setup(tests.blank_slate, tests.nuke_zone)
def test_raise_not_found_on_missing_template_add():
    pdorclient.Zone.from_template(name=tests.TEST_DATA_ZONE,
      template='Derp',
      type=pdorclient.Zone.TYPE_MASTER)

@raises(pdorclient.errors.Rfc952ViolationError)
def test_raise_rfc952_violation_on_nonsense_name():
    pdorclient.Zone.from_template('example!com',
      template='East Coast Data Center',
      type=pdorclient.Zone.TYPE_MASTER)

@raises(NotImplementedError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_add_empty_template():
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
