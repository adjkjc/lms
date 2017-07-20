# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import logging
import filelock


log = logging.getLogger(__name__)


class AuthData(object):
    """
    A simple config db.

    Contains records like so:

    "93820000000000002": {        # situation 1 in the install doc: admin provided key/secret
      "canvas_server_host": "hypothesis.instructure.com",
      "canvas_server_port": null,
      "canvas_server_scheme": "https",
      "lti_refresh_token": "9382~yRo ... Rlid9UXLhxfvwkWDnj",        # this was written back after oauth
      "lti_token": "9382~IAbeGEFScV  ... IIMaEdK3dXlm2d9cjozd",      # this was written back after oauth
      "secret": "tJzcNSZadqlHTCW6ow  ... wodX3dfeuIokkLMjrQJqw3Y2"   # from the canvas dev key/secret record
    },
     "jaimejordan": {       # situation 2: teacher created a token, we installed it and created the key/secret
      "canvas_server_host": "hypothesis.instructure.com",
      "canvas_server_port": null,
      "canvas_server_scheme": "https",
      "lti_refresh_token": null,                      # unused because token hardcoded in this case
      "lti_token": "9382~IAbeGEFSc ... VGmtBU",       # token generated by teacher (canvas "approved integration")
      "secret": "jaimejordan"
    },

    """

    def __init__(self):
        self.name = 'canvas-auth.json'
        self.auth_data = {}
        self.load()

    def set_tokens(self, oauth_consumer_key, lti_token, lti_refresh_token):
        assert oauth_consumer_key in self.auth_data
        lock = filelock.FileLock("authdata.lock")
        with lock.acquire(timeout=1):
            self.auth_data[oauth_consumer_key]['lti_token'] = lti_token
            self.auth_data[oauth_consumer_key]['lti_refresh_token'] = lti_refresh_token
            self.save()

    def get_lti_token(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['lti_token']

    def get_lti_refresh_token(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['lti_refresh_token']

    def get_lti_secret(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['secret']

    def get_canvas_server_scheme(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['canvas_server_scheme']

    def get_canvas_server_host(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['canvas_server_host']

    def get_canvas_server_port(self, oauth_consumer_key):
        return self.auth_data[oauth_consumer_key]['canvas_server_port']

    def get_canvas_server(self, oauth_consumer_key):
        canvas_server_scheme = self.get_canvas_server_scheme(oauth_consumer_key)
        canvas_server_host = self.get_canvas_server_host(oauth_consumer_key)
        canvas_server_port = self.get_canvas_server_port(oauth_consumer_key)
        canvas_server = None
        if canvas_server_port is None:
            canvas_server = '%s://%s' % (canvas_server_scheme, canvas_server_host)
        else:
            canvas_server = '%s://%s:%s' % (canvas_server_scheme, canvas_server_host, canvas_server_port)
        return canvas_server

    def load(self):
        file_ = open(self.name)
        self.auth_data = json.loads(file_.read())
        for key in self.auth_data.keys():
            log.info('key: {key}', key=key)
        file_.close()

    def save(self):
        file_ = open(self.name, 'wb')
        j = json.dumps(self.auth_data, indent=2, sort_keys=True)
        file_.write(j)
        file_.close()