#!/usr/bin/env python
import os.path

import jinja2
import webapp2
import httplib2
from oauth2client.appengine import AppAssertionCredentials
from apiclient.discovery import build
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import memcache
#from google.appengine.api import app_identity

import models
import json
from models import Candidate

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


_PROJECT_ID = 'bigquery-e2e'

#access_token = app_identity.get_access_token(
#    'https://www.googleapis.com/auth/bigquery')
#print access_token
#if access_token[0].find('InvalidToken') > -1:
# openssl pkcs12 -in key.p12 -out key.pem -nodes -nocerts
# openssl rsa -in key.pem -out key-rsa.pem
# use key-rsa.pem
if False:
  from dev_auth.auth import get_bigquery
  bigquery = get_bigquery()
else:
  credentials = AppAssertionCredentials(
      scope='https://www.googleapis.com/auth/bigquery')
  bigquery = build('bigquery', 'v2',
                   http=credentials.authorize(httplib2.Http(memcache)))

datasets = bigquery.datasets()
tables = bigquery.tables()

class MainHandler(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    response = tables.list(projectId=_PROJECT_ID, datasetId='reference').execute()
    
    self.response.write(template.render({
      'tables': [{
          'dataset': entry['tableReference']['datasetId'],
          'name': entry['tableReference']['tableId'],
      } for entry in response['tables']]}))

class ManageDevicesHandler(webapp2.RequestHandler):
  @login_required
  def get(self):
    user = users.get_current_user()
    self._show(user)

  def _show(self, user):
    candidate = None
    for c in models.Candidate.by_owner(user):
      candidate = c
      break
    if not candidate:
      candidate = Candidate()
      candidate.owner = user
      candidate.put()
    data = {
      'user': user,
      'devices': [{
        'id': device.key.id(),
        'added': device.added.strftime('%c'),
        'make': device.make,
        'model': device.model,
        'zip': device.home_zip5,
      } for device in models.Device.by_owner(user)],
      'registration_id': candidate.key.id()
    }
    template = JINJA_ENVIRONMENT.get_template('templates/manage.html')
    self.response.write(template.render(data))

  def post(self):
    user = users.get_current_user()
    if user is None:
      self.abort(401, 'Must be logged in to manage devices.')
    action = self.request.get('action')
    if action == 'Add':
      self._handle_add(user)
    elif action == 'X':
      self._handle_remove()
    else:
      self.abort(400, detail=('Unsupported action %s' % action))
    self.redirect(self.request.route.build(
        self.request, [], {}))

  def _handle_add(self, user):
    device = models.NewDevice()
    device.owner = user
    device.set(self.request)
    device.put()

  def _handle_remove(self):
    models.Device.key_from_id(self.request.get('id')).delete()

class _JsonHandler(webapp2.RequestHandler):
  MAX_PAYLOAD_SIZE = 16 * 1024

  def post(self):
    if self.request.headers.get('Content-Type') != 'application/json':
      self.response.set_status(
          403, message='Expected Content-Type: application/json')
      return
    if len(self.request.body) > self.MAX_PAYLOAD_SIZE:
      self.response.set_status(
          403, message=('Max payload size (%d) exceeded' %
                        self.MAX_PAYLOAD_SIZE))
      return
    try:
      arg = json.loads(self.request.body)
    except ValueError, e:
      self.response.set_status(
          403, message='Could not parse body as json: ' + str(e))
      return
    self.response.headers['Content-Type'] = 'application/json'
    try:
      result = json.dumps(self.handle(arg))
    except Exception, e:
      result = self.json_error(e)
    print result
    self.response.out.write(result)

  def json_error(self, e):
    return json.dumps({'error': e.__class__.__name__,
                       'message': e.message})
    
  def handle(self, arg):
    raise NotImplementedError

class RegisterHandler(_JsonHandler):
  def handle(self, arg):
    device_id = arg.get('id', 'missing')
    candidate = models.Candidate.get_by_id(device_id)
    if not candidate:
      raise KeyError('Id %s not valid' % device_id)
    candidate.register(arg)
    return {}

app = webapp2.WSGIApplication([
    webapp2.Route(r'/', handler=MainHandler, name='main'),
    webapp2.Route(r'/manage', handler=ManageDevicesHandler, name='manage'),
    webapp2.Route(r'/command/register', handler=RegisterHandler, name='register'),
], debug=True)