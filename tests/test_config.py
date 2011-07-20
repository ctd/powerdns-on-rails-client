from nose.tools import raises, with_setup
import httplib2
import logging
import pdorclient
import pdorclient.errors
import tests

logger = logging.getLogger(__name__)

def test_has_tester_defined_config():
    config = pdorclient.Config()

@raises(pdorclient.errors.MissingConfigurationError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_what_happens_on_missing_config():
    config = pdorclient.Config()

def test_fall_back_on_default_config_path():
    # Fall back on ``tests.CONFIG`` in ``$PWD``.
    config = pdorclient.Config(path='yep')

@raises(AttributeError)
def test_raises_attribute_error_on_derp():
    config = pdorclient.Config()
    config.derp

def test_for_something_that_looks_like_a_url():
    config = pdorclient.Config()
    url = config.url
    assert isinstance(url, str)
    assert url.startswith('http')
    assert not url.endswith('/')

def test_for_something_that_looks_like_a_set_of_credentials():
    config = pdorclient.Config()
    (username, password) = config.credentials
    assert isinstance(username, str)
    assert isinstance(password, str)
    assert len(username) > 0
    assert len(password) > 0

def test_auth_credentials_are_actually_valid():
    config = pdorclient.Config()
    url = config.url
    (username, password) = config.credentials
    http = httplib2.Http()
    http.add_credentials(username, password)
    resp, content = http.request('%s/domains' % url,
      headers={'Accept': 'application/xml'}, redirections=0)
    assert resp.status == 200, 'Username and password were not accepted'
