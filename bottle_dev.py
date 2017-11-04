#!python
import os
devenv = False
try:
    if os.environ['USERDOMAIN'].upper() == 'TOSHIBALAPTOP':
        devenv = True
except:
    pass
    
if devenv:
    print "DEVELOPMENT ENVIRONMENT"
    root = "./"
else:
    print "PRODUCTION ENVIRONMENT"
    root = "/home/jeggles/mysite"
staticroot = root + "/static"
pageroot = root + "/pages"
sessionroot = root + "/sessions"
cacheroot = root + "/cache"
libroot = root + "/lib"
print libroot

import sys, re
sys.path.insert(0,libroot)
from wombatwiki.parser import *
from wombatwiki import emoticons, interwiki
import bottle
bottle.debug(True)
from bottle import mako_view as view
from bottle import static_file, request, redirect, hook
bottle.TEMPLATE_PATH.insert(0,root + "/views/")
import beaker.middleware
#from bottle.ext import beaker
#import cgi
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.data_dir': sessionroot,
    'session.auto': True
}
app = bottle.default_app()
application = beaker.middleware.SessionMiddleware(app, session_opts)

# Error handling helper function
def eh():
    html = '<hr><pre>'
    html += '\r\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
    html += '</pre>'
    return html

def dbgprt(*items):
    text = ' '.join([str(i) for i in items])
    print '<pre>%s</pre><br>' % text

class NullCache(object):
    def __init__(self, min_entries=500, max_entries=1000):
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.cachedata = {}
    def update(self, key, newval):
        pass
    def get(self, key):
        raise KeyError
    def has_key(self, key):
        return False
    def remove(self,key):
        pass
    def shrink(self):
        pass
    def __str__(self):
        return str(self.cachedata)

class MemCache(NullCache):
    def __init__(self, min_entries=500, max_entries=1000):
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.cachedata = {}
    def update(self, key, newval):
        if len(self.cachedata) > self.max_entries:
            self.shrink()
        count,val = self.cachedata.get(key,(0,''))
        self.cachedata[key] = (count+1, newval)
    def get(self, key):
        return self.cachedata[key][1]
    def has_key(self, key):
        return self.cachedata.has_key(key)
    def remove(self,key):
        try:
            del self.cachedata[key]
        except KeyError:
            pass
    def shrink(self):
        items = [(v[0],k) for k,v in self.cachedata.items()]
        items.sort()
        for i in range(0, self.max_entries - self.min_entries):
            del self.cachedata[items[1]]


class WikiPage(object):
    pageroot = pageroot
    def __init__(self,page,pagecache=MemCache()):
        self.pagecache = pagecache
        self.page = page
        self.wikitext = ''
        self.wikihtml = ''
        self.wikiparser = WikiParser()
    def iswikiname(self,name):
        return re.match(r'(^[A-Z]+[a-z]+-*[_A-Z0-9][_A-Za-z0-9]+$)', name) is not None
        #return re.match('^([A-Z][a-z]+){2,}$', name) is not None
    def formatwikiname(self):
        return formatwikiname(self.page)
    def getwikitext(self):
        if not self.wikitext:
            pagefile = os.path.join(self.pageroot, self.page)
            if not os.path.isfile(pagefile):
                return None
            self.wikitext = open(pagefile).read()
        return self.wikitext
    def savewikitext(self, text):
        pagefile = os.path.join(self.pageroot, self.page)
        open(pagefile,'w').write(text)
        self.pagecache.remove(self.page)
    def getwikihtml(self):
        try:
            return self.pagecache.get(self.page)
        except KeyError:
            print "Cached page not found", self.page
        if not self.wikihtml:
            self.wikihtml = self.wikiparser(self.page, self.getwikitext())
        self.pagecache.update(self.page, self.wikihtml)
        return self.wikihtml

def getwikipagelist(pageroot=pageroot):
    pages = os.listdir(pageroot)
    pages.sort()
    return pages

@hook('before_request')
def setup_request():
    request.session = request.environ.get('beaker.session',[])

@app.route('/<filename:re:.*\..*>')
def send_file(filename):
    return static_file(filename, root=staticroot)

@app.route('/')
@app.route('/<page>')
@app.route('/<page>/')
@view('wikishow.mako',output_encoding='utf-8')
def show(page='FrontPage'):
    searchtext = request.forms.get('searchtext', '')
    wikipage = WikiPage(page)
    wikihtml = wikipage.getwikihtml()
    print wikihtml
    errmsg = ''
    if wikihtml is None:
        #~ return edit(page=page)
        #~ errmsg = '%s not found.' % page
        #~ page = "FrontPage"
        #~ wikipage = WikiPage(page)
        #~ wikihtml = wikipage.getwikihtml()
        wikihtml = 'Page does not exist. <a href="'+page+'/edit">Click here to create.</a>'
        errmsg = '' # Page not found'
    print("Showing",page)
    visited = processvisited(request.session.get('visited', []), page)
    request.session['visited'] = visited
    breadcrumbs = formatbreadcrumbs(visited)
    title = wikipage.formatwikiname()
    return dict(action='show', page=page, title=title, searchtext=searchtext, wikihtml=wikihtml, errmsg=errmsg, breadcrumbs=breadcrumbs)

@app.route('/<page>/edit')
@view('wikiedit.mako',output_encoding='utf-8')
def edit(page='FrontPage'):
    wikipage = WikiPage(page)
    wikitext = wikipage.getwikitext() or ""
    errmsg = ''
    #~ if wikitext is None:
        #~ errmsg = '%s not found.' % page
        #~ page = "FrontPage"
        #~ pagefile = os.path.join(pageroot, page)
    print("Editing", page)
    title = wikipage.formatwikiname()
    return dict(action='edit', page=page, title=title, wikitext=wikitext, errmsg=errmsg)

@app.route('/<page>/edit', method='POST')
def save(page=None):
    if page is None:
        page = 'FrontPage'
        redirect('/%s' % page)
    wikipage = WikiPage(page)
    print("Saving", page)
    newtext = request.forms.get('newtext')
    wikipage.savewikitext(newtext)
    redirect('/%s' % page)

@app.route('/search')
@view('wikisearch.mako',output_encoding='utf-8')
def searchform():
    return dict(action='show', page='Search', title='', searchtext='', searchhint='Enter search criteria', wikihtml='', errmsg='', breadcrumbs='')


@app.route('/search', method='POST')
@view('wikisearch.mako',output_encoding='utf-8')
def search():
    searchtext = request.forms.get('searchtext', '')
    wikihtml = searchtext + " not found"
    if searchtext:
        titlehits, texthits = [], []
        p = re.compile(searchtext, re.I + re.M)
        for page in getwikipagelist():
            wikipage = WikiPage(page)
            wikitext = wikipage.getwikitext()
            title = wikipage.formatwikiname()
            titlehits.append((page, p.search(title)))
            texthits.append((len(p.findall(wikitext)), page))
        titlehits.sort()
        texthits.sort(); texthits.reverse()
        wikitext = '''__Matches for: %s__\n___Title matches___\n * %s\n----
        \n___Text matches (& number of matches)___\n * %s
        ''' % (searchtext, '\n * '.join([i[0] for i in titlehits if i[1]]) or '[None]',
               '\n * '.join(['%s (%s)' % (i[1], i[0]) for i in texthits if i[0]]) or '[None]')
        wikiparser = WikiParser()
        wikihtml = wikiparser("SearchResults",wikitext)
    return dict(action='show', page='Search', title='', searchtext=searchtext, searchhint='', wikihtml=wikihtml, errmsg='', breadcrumbs='')


bottle.run(app=application, host='localhost', port=8080, server="tornado")
