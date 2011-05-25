from nose.tools import raises, with_setup
import datetime
import logging
import pdorclient
import pdorclient.errors
import tests
import time

logger = logging.getLogger(__name__)

@raises(pdorclient.errors.PrematurePersistError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_premature_on_early_persist():
    record = pdorclient.Record(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Record.TYPE_NS,
      content='ns1.%s' % tests.TEST_DATA_ZONE,
      ttl=600,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    record.save()

@with_setup(tests.blank_slate, None)
@with_setup(tests.disappear_config, tests.restore_config)
def test_lookup_seeded():
    zone = pdorclient.Zone.lookup('example.com',
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    a_count = 0
    mx_count = 0
    ns_count = 0
    soa_count = 0

    for r in zone.records:
        logging.debug('%r' % r)

        assert isinstance(r, pdorclient.Record)

        if r.type == pdorclient.Record.TYPE_A:
            a_count += 1
        if r.type == pdorclient.Record.TYPE_MX:
            mx_count += 1
        if r.type == pdorclient.Record.TYPE_NS:
            ns_count += 1
        if r.type == pdorclient.Record.TYPE_SOA:
            soa_count += 1

    total_count = a_count + mx_count + ns_count + soa_count

    assert a_count == 4
    assert mx_count == 1
    assert ns_count == 2
    assert soa_count == 1
    assert len(zone.records) == total_count

@with_setup(tests.blank_slate, None)
@with_setup(tests.disappear_config, tests.restore_config)
def test_record_sorting():
    zone = pdorclient.Zone.lookup('example.com',
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    records = sorted(zone.records)
    assert records[0].rtype == 'A'

@with_setup(tests.blank_slate, None)
@with_setup(tests.disappear_config, tests.restore_config)
def test_add_zone():
    zone = pdorclient.Zone(name=tests.TEST_DATA_ZONE,
      type=pdorclient.Zone.TYPE_MASTER,
      ttl=600,
      notes=tests.TEST_DATA_NOTES,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.records = [
      pdorclient.Record(name=tests.TEST_DATA_ZONE,
        type=pdorclient.Record.TYPE_NS,
        content='ns1.%s' % tests.TEST_DATA_ZONE,
        ttl=600,
        config=pdorclient.Config(path=tests.TMP_CONFIG)),
      pdorclient.Record(name=tests.TEST_DATA_ZONE,
        type=pdorclient.Record.TYPE_NS,
        content='ns2.%s' % tests.TEST_DATA_ZONE,
        ttl=600,
        config=pdorclient.Config(path=tests.TMP_CONFIG)),
      pdorclient.Record(name=tests.TEST_DATA_ZONE,
        type=pdorclient.Record.TYPE_SOA,
        content=tests.TEST_DATA_SOA,
        ttl=600,
        config=pdorclient.Config(path=tests.TMP_CONFIG)),
      pdorclient.Record(name='ns1.%s' % tests.TEST_DATA_ZONE,
        type=pdorclient.Record.TYPE_A,
        content='1.2.3.4',
        ttl=600,
        config=pdorclient.Config(path=tests.TMP_CONFIG)),
      pdorclient.Record(name='ns2.%s' % tests.TEST_DATA_ZONE,
        type=pdorclient.Record.TYPE_A,
        content='4.3.2.1',
        ttl=600,
        config=pdorclient.Config(path=tests.TMP_CONFIG)),
    ]

    logging.debug('zone before save(): %r' % zone)
    for r in zone.records:
        assert r._state == r.STATE_NEW
        assert r.id == None
        assert r.domain_id == None
        assert r.created_at == None
        assert r.updated_at == None

    zone.save()

    logging.debug('zone after save(): %r' % zone)
    for r in zone.records:
        logging.debug('Scrutinising record %r' % r)
        assert r._state == r.STATE_AT_REST
        assert r.id != None
        assert zone.id != None
        assert r.domain_id == zone.id
        assert isinstance(r.created_at, datetime.datetime)
        assert isinstance(r.updated_at, datetime.datetime)
        assert r.updated_at >= r.created_at

@with_setup(tests.disappear_config, tests.restore_config)
def test_persistence():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    assert len(zone.records) == 5

    # We make no guarantees on the order in which these records are 
    # returned!
    for r in zone.records:
        logging.debug('Scrutinising record %r' % r)
        assert r._state == r.STATE_AT_REST
        assert r.id != None
        assert zone.id != None
        assert r.domain_id == zone.id
        assert isinstance(r.created_at, datetime.datetime)
        assert isinstance(r.updated_at, datetime.datetime)
        assert r.updated_at >= r.created_at

@with_setup(tests.disappear_config, tests.restore_config)
def test_update():
    TEST_DATA_CONTENT = '5.5.5.5'

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))

    # Locate the RR we want to update.  Normally, you would want to 
    # search by name and type, but I'm not particularly fussed here.  
    # Edit the first A record we find.
    for r in zone.records:
        if r.type == r.TYPE_A:
            record = r
            break
    else: # pragma: no cover
        assert False, \
          'Your test data should contain at least one A record'

    before = record.updated_at
    assert record._state == record.STATE_AT_REST
    assert record.content != TEST_DATA_CONTENT
    record.content = TEST_DATA_CONTENT
    assert record._state == record.STATE_DIRTY

    # Modifying a child resource will *not* change the parent resource's 
    # state.  This is not a bug.  The parent has not been modified.
    assert zone._state == zone.STATE_AT_REST

    assert record.content == TEST_DATA_CONTENT
    logging.debug('zone before save(): %r' % zone)

    time.sleep(2)
    zone.save()

    logging.debug('zone after save(): %r' % zone)
    assert record._state == record.STATE_AT_REST
    assert record.content == TEST_DATA_CONTENT
    after = record.updated_at
    delta = after - before
    logging.debug('delta=%r' % delta)
    assert delta > datetime.timedelta(seconds=1)
    assert delta < datetime.timedelta(seconds=5)

@raises(pdorclient.errors.ReadOnlyAttributeError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_read_only_error_on_write_to_id():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.records[0].id = 3

@raises(pdorclient.errors.ReadOnlyAttributeError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_raise_read_only_error_on_write_to_last_check():
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    zone.records[0].domain_id = 1000

@with_setup(tests.disappear_config, tests.restore_config)
def test_remove_record():
    """Query for all zone resource records and remove only a single RR
    from the set of results.  All other resource records must remain.

    """
    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    before = len(zone.records)
    logging.debug('zone before delete(): %r' % zone)

    record = zone.records[0]
    record.delete()
    assert record._state == pdorclient.Record.STATE_DELETED
    assert record.id == None

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    after = len(zone.records)
    logging.debug('zone after delete(): %r' % zone)

    assert before - 1 == after

@with_setup(None, tests.nuke_zone)
@with_setup(tests.disappear_config, tests.restore_config)
def test_selective_query_and_remove():
    """Query for, and remove, only the two ``ns*`` DNS A resource
    records.  All other resource records should remain.

    """
    N_NS_A_RECORDS = 2

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    before = len(zone.records)

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      match='ns',
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    assert len(zone.records) == N_NS_A_RECORDS
    for r in zone.records:
        r.delete()
    zone.save()

    zone = pdorclient.Zone.lookup(tests.TEST_DATA_ZONE,
      config=pdorclient.Config(path=tests.TMP_CONFIG))
    after = len(zone.records)
    assert before - N_NS_A_RECORDS == after
