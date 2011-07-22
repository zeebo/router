#!/usr/bin/env python
#Requirements:
#	paste
#	django
#	werkzeug
#	wsgiproxy
#	-lots of configuration-

#	script must be run with root permission

from werkzeug.wsgi import get_host, get_current_url, responder
from werkzeug.wrappers import Request, Response
from wsgiproxy.exactproxy import proxy_exact_request
import django.core.handlers.wsgi
import django.conf
import os, os.path
import sys

BASE_DIR = '/Users/zeebo/Code/sites'
CONF_USER_ID = 501
BACKEND_WEB_PORT = 8080
BACKEND_ROUTER_IP = '127.0.0.1'
BACKEND_ROUTER_PORT = 80
BACKEND_PID_FILE = '/var/run/httpd.pid'

def drop_last(data, token='.'):
	return token.join(data.split(token)[:-1])

def is_django(host):
	settings_name = '{}.settings'.format(host)
	if BASE_DIR not in sys.path:
		sys.path.insert(0, BASE_DIR)
	try:
		settings = __import__(settings_name, {}, {}, None)
		return True
	except ImportError, ValueError:
		return False
	finally:
		if settings_name in sys.modules:
			del sys.modules[settings_name]

def restart_apache():
	#can't just call apachectl restart becuase it exits before
	#apache comes back up.

	with open(BACKEND_PID_FILE) as pid_file:
		pid = pid_file.read().strip()
	import subprocess
	subprocess.call(['kill', '-USR1', pid])

def make_apache_confs(host):
	#Check if the conf file exists.
	#if so, abort!
	conf_dir = os.path.join(BASE_DIR, 'conf')
	conf_filename = '{}.conf'.format(host)
	if os.path.exists(os.path.join(conf_dir, conf_filename)):
		return
	with open('conf.template') as conf_template:
		template_string = conf_template.read()
		with open(os.path.join(conf_dir, conf_filename), 'w') as handle:
			handle.write(template_string.format(host))
		os.chown(os.path.join(conf_dir, conf_filename), CONF_USER_ID, -1)

	#Now tell apache to restart
	restart_apache()

def wrap_wsgi(handler, host):
	def wrapped(environ, start_response):
		full_path = os.path.realpath(os.path.join(BASE_DIR, host))
		activate_this = os.path.join(full_path, '../bin/activate_this.py')
		previous_path = sys.path[:]
		try:
			execfile(activate_this, dict(__file__=activate_this))
			sys.path.insert(0, full_path)
			return handler(environ, start_response)
		finally:
			sys.path = previous_path
	return wrapped

def make_django_app(host):
	def django_app():
		os.environ['DJANGO_SETTINGS_MODULE'] = '{}.settings'.format(host)

		reload(django.conf)
		reload(django.core.handlers.wsgi)
		from django.core.handlers.wsgi import WSGIHandler
		return wrap_wsgi(WSGIHandler(), host)

	return django_app

def forwarding_app():
	def forwarding(environ, start_response):
		environ['SERVER_PORT'] = BACKEND_WEB_PORT
		return proxy_exact_request(environ, start_response)
	return forwarding

@Request.application
def error_app(request):
	return Response('App does not exist')

def conf_app():
	@Request.application
	def app(request):
		return Response('Conf app')
	return app

def dispatcher(environ, start_response, handlers={'conf': conf_app}):
	host = drop_last(get_host(environ))
	
	if not os.path.exists(os.path.join(BASE_DIR, host)):
		if host in handlers:
			del handlers[host]
		return error_app(environ, start_response)

	if host in handlers:
		return handlers[host]()(environ, start_response)

	if is_django(host):
		app = make_django_app(host)
	else:
		app = forwarding_app
		make_apache_confs(host)

	handlers[host] = app
	return app()(environ, start_response)

if __name__ == '__main__':
	from werkzeug.serving import run_simple
	args = {
		'use_reloader': True,
		'threaded': True,
		'use_debugger': True,
	}
	run_simple(BACKEND_ROUTER_IP, BACKEND_ROUTER_PORT, dispatcher, **args)