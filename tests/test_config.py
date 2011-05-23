from nose.tools import raises, with_setup
import httplib2
import logging
import pdorclient
import pdorclient.errors
import tests

logger = logging.getLogger(__name__)

def test_config():
    """Has the tester defined our configuration for us?"""
    config = pdorclient.Config()

@raises(pdorclient.errors.MissingConfigurationError)
@with_setup(tests.disappear_config, tests.restore_config)
def test_no_config():
    """What happens when we are missing our configuration?"""
    config = pdorclient.Config()

def test_custom_config_path():
    # Fall back on ``tests.CONFIG`` in ``$PWD``.
    config = pdorclient.Config(path='yep')

@raises(AttributeError)
def test_raises_attribute_error_on_derp():
    config = pdorclient.Config()
    config.derp

def test_url_exists():
    """Has the tester defined what looks like a valid URL?"""
    config = pdorclient.Config()
    url = config.url
    assert isinstance(url, str)
    assert url.startswith('http')
    assert not url.endswith('/')

def test_credentials_exist():
    """Has the tester defined credentials?"""
    config = pdorclient.Config()
    (username, password) = config.credentials
    assert isinstance(username, str)
    assert isinstance(password, str)
    assert len(username) > 0
    assert len(password) > 0

def test_auth():
    """Open sesame..!  Did the door open?"""
    config = pdorclient.Config()
    url = config.url
    (username, password) = config.credentials
    http = httplib2.Http()
    http.add_credentials(username, password)
    resp, content = http.request('%s/domains' % url,
      headers={'Accept': 'application/xml'}, redirections=0)
    assert resp.status == 200, 'Username and password were not accepted'
