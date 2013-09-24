############################################################
#
# Autogenerated by the KBase type compiler -
# any changes made here will be overwritten
#
# Passes on URLError, timeout, and BadStatusLine exceptions.
#     See: 
#     http://docs.python.org/2/library/urllib2.html
#     http://docs.python.org/2/library/httplib.html
#
############################################################

try:
    import json
except ImportError:
    import sys
    sys.path.append('simplejson-2.3.3')
    import simplejson as json
    
import urllib2, httplib, urlparse, random, base64, httplib2
from urllib2 import URLError, HTTPError
from ConfigParser import ConfigParser
import os

_CT = 'content-type'
_AJ = 'application/json'
_URL_SCHEME = frozenset(['http', 'https']) 

# This is bandaid helper function until we get a full
# KBase python auth client released
def _get_token( user_id, password,
                auth_svc="https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials"):
    h = httplib2.Http( disable_ssl_certificate_validation=True)
    
    auth = base64.encodestring( user_id + ':' + password )
    headers = { 'Authorization' : 'Basic ' + auth }
    
    h.add_credentials(user_id, password)
    h.follow_all_redirects = True
    url = auth_svc
    
    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    if status>=200 and status<=299:
        tok = json.loads(content)
    elif status == 403: 
        raise Exception( "Authentication failed: Bad user_id/password combination %s:%s" % (user_id, password))
    else:
        raise Exception(str(resp))
        
    return tok['access_token']

# Another bandaid to read in the ~/.authrc file if one is present
def _read_rcfile( file=os.environ['HOME']+"/.authrc"):
    authdata = None
    if os.path.exists( file):
        try:
            with open( file ) as authrc:
                rawdata = json.load( authrc)
                # strip down whatever we read to only what is legit
                authdata = { x : rawdata.get(x) for x in ( 'user_id', 'auth_token',
                                                           'client_secret', 'keyfile',
                                                           'keyfile_passphrase','password')}
        except Exception, e:
            print "Error while reading authrc file %s: %s" % (file, e)
    return authdata

# Another bandaid to read in the ~/.kbase_config file if one is present
def _read_inifile( file=os.environ.get('KB_DEPLOYMENT_CONFIG',os.environ['HOME']+"/.kbase_config")):
    authdata = None
    if os.path.exists( file):
        try:
            config = ConfigParser()
            config.read(file)
            # strip down whatever we read to only what is legit
            authdata = { x : config.get('authentication',x) if config.has_option('authentication',x) else None for x in
                         ( 'user_id', 'auth_token','client_secret', 'keyfile','keyfile_passphrase','password') }
        except Exception, e:
            print "Error while reading INI file %s: %s" % (file, e)
    return authdata

class ServerError(Exception):

    def __init__(self, name, code, message):
        self.name = name
        self.code = code
        self.message = '' if message is None else message

    def __str__(self):
        return self.name + ': ' + str(self.code) + '. ' + self.message
        
class JSONObjectEncoder(json.JSONEncoder):
  
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, frozenset):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

class IDServerAPI:

    def __init__(self, url = None, timeout = 30 * 60, user_id = None, 
                 password = None, token = None, ignore_authrc = False):
        if url is None:
            raise ValueError('A url is required')
        scheme, _, _, _, _, _ = urlparse.urlparse(url)
        if scheme not in _URL_SCHEME:
            raise ValueError(url + " isn't a valid http url")
        self.url = url
        self.timeout = int(timeout)
        self._headers = dict()
        # token overrides user_id and password
        if token is not None:
            self._headers['AUTHORIZATION'] = token
        elif user_id is not None and password is not None:
            self._headers['AUTHORIZATION'] = _get_token( user_id, password)
        elif 'KB_AUTH_TOKEN' in os.environ:
            self._headers['AUTHORIZATION'] = os.environ.get('KB_AUTH_TOKEN')
        elif not ignore_authrc:
            authdata = _read_inifile()
            if authdata is None:
                authdata = _read_rcfile()
            if authdata is not None:
                if authdata.get('auth_token') is not None:
                    self._headers['AUTHORIZATION'] = authdata['auth_token']
                elif authdata.get('user_id') is not None and authdata.get('password') is not None:
                    self._headers['AUTHORIZATION'] = _get_token( authdata['user_id'],authdata['password'] )
        if self.timeout < 1:
            raise ValueError('Timeout value must be at least 1 second')

    def kbase_ids_to_external_ids(self, ids):

        arg_hash = { 'method': 'IDServerAPI.kbase_ids_to_external_ids',
                     'params': [ids],
                     'version': '1.1',
                     'id': str(random.random())[2:]
                     }

        body = json.dumps(arg_hash, cls = JSONObjectEncoder)
        try:
            request = urllib2.Request( self.url, body, self._headers)
#            ret = urllib2.urlopen(self.url, body, timeout = self.timeout)
            ret = urllib2.urlopen(request, timeout = self.timeout)
        except HTTPError as h:
            if _CT in h.headers and h.headers[_CT] == _AJ:
                b = h.read()
                err = json.loads(b) 
                if 'error' in err:
                    raise ServerError(**err['error'])
                else:            #this should never happen... but if it does 
                    se = ServerError('Unknown', 0, b)
                    se.httpError = h
                    raise se
                    #raise h      #  h.read() will return '' in the calling code.
            else:
                raise h
        if ret.code != httplib.OK:
            raise URLError('Received bad response code from server:' + ret.code)
        resp = json.loads(ret.read())

        if 'result' in resp:
            return resp['result'][0]
        else:
            raise ServerError('Unknown', 0, 'An unknown server error occurred')

    def external_ids_to_kbase_ids(self, external_db, ext_ids):

        arg_hash = { 'method': 'IDServerAPI.external_ids_to_kbase_ids',
                     'params': [external_db, ext_ids],
                     'version': '1.1',
                     'id': str(random.random())[2:]
                     }

        body = json.dumps(arg_hash, cls = JSONObjectEncoder)
        try:
            request = urllib2.Request( self.url, body, self._headers)
#            ret = urllib2.urlopen(self.url, body, timeout = self.timeout)
            ret = urllib2.urlopen(request, timeout = self.timeout)
        except HTTPError as h:
            if _CT in h.headers and h.headers[_CT] == _AJ:
                b = h.read()
                err = json.loads(b) 
                if 'error' in err:
                    raise ServerError(**err['error'])
                else:            #this should never happen... but if it does 
                    se = ServerError('Unknown', 0, b)
                    se.httpError = h
                    raise se
                    #raise h      #  h.read() will return '' in the calling code.
            else:
                raise h
        if ret.code != httplib.OK:
            raise URLError('Received bad response code from server:' + ret.code)
        resp = json.loads(ret.read())

        if 'result' in resp:
            return resp['result'][0]
        else:
            raise ServerError('Unknown', 0, 'An unknown server error occurred')

    def register_ids(self, prefix, db_name, ids):

        arg_hash = { 'method': 'IDServerAPI.register_ids',
                     'params': [prefix, db_name, ids],
                     'version': '1.1',
                     'id': str(random.random())[2:]
                     }

        body = json.dumps(arg_hash, cls = JSONObjectEncoder)
        try:
            request = urllib2.Request( self.url, body, self._headers)
#            ret = urllib2.urlopen(self.url, body, timeout = self.timeout)
            ret = urllib2.urlopen(request, timeout = self.timeout)
        except HTTPError as h:
            if _CT in h.headers and h.headers[_CT] == _AJ:
                b = h.read()
                err = json.loads(b) 
                if 'error' in err:
                    raise ServerError(**err['error'])
                else:            #this should never happen... but if it does 
                    se = ServerError('Unknown', 0, b)
                    se.httpError = h
                    raise se
                    #raise h      #  h.read() will return '' in the calling code.
            else:
                raise h
        if ret.code != httplib.OK:
            raise URLError('Received bad response code from server:' + ret.code)
        resp = json.loads(ret.read())

        if 'result' in resp:
            return resp['result'][0]
        else:
            raise ServerError('Unknown', 0, 'An unknown server error occurred')

    def allocate_id_range(self, kbase_id_prefix, count):

        arg_hash = { 'method': 'IDServerAPI.allocate_id_range',
                     'params': [kbase_id_prefix, count],
                     'version': '1.1',
                     'id': str(random.random())[2:]
                     }

        body = json.dumps(arg_hash, cls = JSONObjectEncoder)
        try:
            request = urllib2.Request( self.url, body, self._headers)
#            ret = urllib2.urlopen(self.url, body, timeout = self.timeout)
            ret = urllib2.urlopen(request, timeout = self.timeout)
        except HTTPError as h:
            if _CT in h.headers and h.headers[_CT] == _AJ:
                b = h.read()
                err = json.loads(b) 
                if 'error' in err:
                    raise ServerError(**err['error'])
                else:            #this should never happen... but if it does 
                    se = ServerError('Unknown', 0, b)
                    se.httpError = h
                    raise se
                    #raise h      #  h.read() will return '' in the calling code.
            else:
                raise h
        if ret.code != httplib.OK:
            raise URLError('Received bad response code from server:' + ret.code)
        resp = json.loads(ret.read())

        if 'result' in resp:
            return resp['result'][0]
        else:
            raise ServerError('Unknown', 0, 'An unknown server error occurred')

    def register_allocated_ids(self, prefix, db_name, assignments):

        arg_hash = { 'method': 'IDServerAPI.register_allocated_ids',
                     'params': [prefix, db_name, assignments],
                     'version': '1.1',
                     'id': str(random.random())[2:]
                     }

        body = json.dumps(arg_hash, cls = JSONObjectEncoder)
        try:
            request = urllib2.Request( self.url, body, self._headers)
#            ret = urllib2.urlopen(self.url, body, timeout = self.timeout)
            ret = urllib2.urlopen(request, timeout = self.timeout)
        except HTTPError as h:
            if _CT in h.headers and h.headers[_CT] == _AJ:
                b = h.read()
                err = json.loads(b) 
                if 'error' in err:
                    raise ServerError(**err['error'])
                else:            #this should never happen... but if it does 
                    se = ServerError('Unknown', 0, b)
                    se.httpError = h
                    raise se
                    #raise h      #  h.read() will return '' in the calling code.
            else:
                raise h
        if ret.code != httplib.OK:
            raise URLError('Received bad response code from server:' + ret.code)
        resp = json.loads(ret.read())

        if 'result' in resp:
            return resp['result']
        else:
            raise ServerError('Unknown', 0, 'An unknown server error occurred')



