from nose.tools import raises, with_setup
import datetime
import logging
import pdorclient
import pdorclient.errors
import tests
import time

logger = logging.getLogger(__name__)

@raises(pdorclient.errors.Rfc952ViolationError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_rfc952_violation_on_nonsense_name():
    zone = pdorclient.Zone.lookup('example!com',
      config=pdorclient.Config(path=tests.TMP_CONFIG))

@with_setup(tests.disappear_config, tests.restore_config)
def test_lookup_seeded():
    zone = pdorclient.Zone.lookup('example.com',
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert isinstance(zone, pdorclient.Zone)
    assert isinstance(zone._id, str) # Internal representation
    assert isinstance(zone.id, int)  # External
    assert zone.id == 1
    assert isinstance(zone.name, str)
    assert zone.name == 'example.com'
    assert zone.type == pdorclient.Zone.TYPE_NATIVE
    assert zone.rtype == 'NATIVE'
    assert isinstance(zone.created_at, datetime.datetime)
    assert isinstance(zone.updated_at, datetime.datetime)
    assert zone.updated_at >= zone.created_at
    assert isinstance(zone.ttl, int)

@with_setup(tests.blank_slate, None)
@with_setup(tests.disappear_config, tests.restore_config)
def test_lookup_seeded_no_rrs():
    zone = pdorclient.Zone.lookup('example.com',
      match=False,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert isinstance(zone, pdorclient.Zone)
    assert isinstance(zone.id, int)  # External
    assert zone.id == 1
    assert isinstance(zone.name, str)
    assert zone.name == 'example.com'

@raises(pdorclient.errors.NameNotFoundError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_not_found_on_missing_zone():
    pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

@with_setup(tests.blank_slate, None)
@with_setup(tests.disappear_config, tests.restore_config)
def test_add_zone():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_MASTER,
      ttl=600,
      notes=tests.TEST_DATA_NOTES,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    logging.debug('zone before save(): %r' % zone)
    assert zone._state == zone.STATE_NEW
    assert zone.id == None
    assert zone.created_at == None
    assert zone.updated_at == None

    zone.save()

    logging.debug('zone after save(): %r' % zone)
    assert zone._state == zone.STATE_AT_REST
    assert zone.id != None
    assert isinstance(zone.created_at, datetime.datetime)
    assert isinstance(zone.updated_at, datetime.datetime)
    assert zone.updated_at >= zone.created_at

@with_setup(tests.disappear_config, tests.restore_config)
def test_persistence():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert isinstance(zone, pdorclient.Zone)
    assert zone._state == zone.STATE_AT_REST
    assert zone.id != None
    assert isinstance(zone.name, str)
    assert zone.name == tests.TEST_DATA_ZONE
    assert zone.master == None
    assert isinstance(zone.ttl, int)
    assert zone.ttl == 600
    assert isinstance(zone.notes, str)
    assert zone.notes == tests.TEST_DATA_NOTES

@with_setup(tests.disappear_config, tests.restore_config)
def test_update():
    TEST_DATA_NOTES = 'Herpy derps'

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    before = zone.updated_at
    assert zone._state == zone.STATE_AT_REST
    assert zone.notes != TEST_DATA_NOTES
    zone.notes = TEST_DATA_NOTES
    assert zone._state == zone.STATE_DIRTY
    assert zone.notes == TEST_DATA_NOTES
    logging.debug('zone before save(): %r' % zone)

    time.sleep(2)
    zone.save()

    logging.debug('zone after save(): %r' % zone)
    assert zone._state == zone.STATE_AT_REST
    assert zone.notes == TEST_DATA_NOTES
    after = zone.updated_at
    delta = after - before
    logging.debug('delta=%r' % delta)
    assert delta > datetime.timedelta(seconds=1)
    assert delta < datetime.timedelta(seconds=6)

@raises(AttributeError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_attribute_error_on_derp():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.derp

@raises(pdorclient.errors.ReadOnlyAttributeError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_read_only_error_on_write_to_id():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.id = 3

@raises(pdorclient.errors.ReadOnlyAttributeError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_read_only_error_on_write_to_last_check():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.last_check = 1000

@with_setup(None, tests.nuke_zone)
@with_setup(tests.disappear_config, tests.restore_config)
def test_remove_zone():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.delete()

    assert isinstance(zone, pdorclient.Zone)
    assert zone._state == zone.STATE_DELETED
    assert zone.id == None

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_no_master():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_MASTER)
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert zone.master is None

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_null_master():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_MASTER,
      master=[])
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert zone.master is None

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_empty_master():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_MASTER,
      master='')
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert zone.master is None

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_single_master():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_SLAVE,
      master='1.2.3.4')
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert isinstance(zone.master, list)
    assert zone.master == ['1.2.3.4',]

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_single_master_with_trailing_comma():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_SLAVE,
      master='1.2.3.4,')
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert isinstance(zone.master, list)
    assert zone.master == ['1.2.3.4',]

@with_setup(tests.blank_slate, tests.nuke_zone)
def test_add_zone_with_multiple_masters():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_SLAVE,
      master='1.2.3.4,9.8.7.6')
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE)
    assert isinstance(zone.master, list)
    assert zone.master == ['1.2.3.4', '9.8.7.6']

@with_setup(tests.blank_slate, tests.nuke_zone)
@with_setup(tests.disappear_config, tests.restore_config)
def test_add_zone_from_template():
    zone = pdorclient.Zone.from_template(
      name=tests.TEST_DATA_ZONE,
      template='East Coast Data Center',
      type=pdorclient.Zone.TYPE_MASTER,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    logging.debug('zone before save(): %r' % zone)
    zone.save()
    logging.debug('zone after save(): %r' % zone)

    # The ``zone`` resource should be usable straight away.
    assert len(zone.records) == 8

    # Ensure all the RRs from the template were cloned and persisted.
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    logging.debug('Reloaded zone: %r' % zone)
    assert len(zone.records) == 8

@raises(pdorclient.errors.IpV4ParseError)
def test_add_zone_with_invalid_master():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_SLAVE,
      master='1.2.3.4.9.8.7.6')
