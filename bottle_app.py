#!python
# -*- coding: UTF-8 -*-
import bottle_config as cfg
import os, sys, re

import bottle, beaker
bottle.debug(True)
from bottle import route, mount, run, hook, request, static_file, redirect, app as apps
from bottle_wiki import application as wikiapp

mainapp = apps.push()

@hook('before_request')
def setup_request():
    request.session = request.environ.get('beaker.session',[])

@route('/<filename:re:.*\..*>')
def send_file(filename):
    return static_file(filename, root=cfg.staticroot)

@route('/')
@route('/home')
def home():
    redirect(cfg.wiki_virtdir)
    
mainapp.mount(cfg.wiki_virtdir, wikiapp)
application = beaker.middleware.SessionMiddleware(mainapp, cfg.session_opts)

# Error handling helper function
def eh():
    html = '<hr><pre>'
    html += '\r\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
    html += '</pre>'
    return html

def dbgprt(*items):
    text = ' '.join([str(i) for i in items])
    print >>sys.stderr, '<pre>%s</pre><br>' % text


if cfg.runtime_env == "DEV": bottle.run(app=application, host='localhost', port=8080, server="tornado")
