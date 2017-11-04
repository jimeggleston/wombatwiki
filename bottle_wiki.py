import bottle_config as cfg  
import os, sys, re
from wombatwiki.parser import *
from wombatwiki import emoticons, interwiki
import bottle
bottle.debug(True)
from bottle import mako_view as view
from bottle import static_file, request, redirect, hook, app as apps
bottle.TEMPLATE_PATH.insert(0,cfg.viewroot)
import beaker.middleware

app = apps.push()
# app = bottle.default_app()
application = beaker.middleware.SessionMiddleware(app, cfg.session_opts)


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

RE_WIKINAME = re.compile(r'(^[A-Z]+[a-z]+-*[_A-Z0-9][_A-Za-z0-9]+$)')

class WikiPage(object):
    pageroot = cfg.pageroot
    def __init__(self,page,pagecache=MemCache()):
        self.pagecache = pagecache
        self.page = page
        self.wikitext = ''
        self.wikihtml = ''
        self.wikiparser = WikiParser(virtualdir=cfg.wiki_virtdir)
    def iswikiname(self,name):
        return bool(RE_WIKINAME.match(name))
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
    def isfile(self):
        pagefile = os.path.join(self.pageroot, self.page)
        return(os.path.isfile(pagefile))
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

def getwikipagelist(pageroot=cfg.pageroot):
    pages = os.listdir(pageroot)
    pages.sort()
    return pages

@hook('before_request')
def setup_request():
    request.session = request.environ.get('beaker.session',[])

@app.route('/<filename:re:.*\..*>')
def send_file(filename):
    return static_file(filename, root=cfg.staticroot)

@app.route('/')
@app.route('/<page>')
@app.route('/<page>/')
@view('wikishow.mako',output_encoding='utf-8')
def show(page='FrontPage'):
    searchtext = request.forms.get('searchtext', '')
    wikipage = WikiPage(page)
    wikihtml = wikipage.getwikihtml()
    # print wikihtml
    errmsg = ''
    if wikihtml is None:
        #~ return edit(page=page)
        #~ errmsg = '%s not found.' % page
        #~ page = "FrontPage"
        #~ wikipage = WikiPage(page)
        #~ wikihtml = wikipage.getwikihtml()
        wikihtml = 'Page does not exist. <a href="'+page+'/edit">Click here to create.</a>'
        errmsg = '' # Page not found'
    # print("Showing",page)
    visited = processvisited(request.session.get('visited', []), page)
    request.session['visited'] = visited
    breadcrumbs = formatbreadcrumbs(visited,virtualdir=cfg.wiki_virtdir)
    title = wikipage.formatwikiname()
    return dict(action='show', virtualdir=cfg.wiki_virtdir, page=page, title=title, searchtext=searchtext, wikihtml=wikihtml, errmsg=errmsg, breadcrumbs=breadcrumbs)

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
    # print("Editing", page)
    title = wikipage.formatwikiname()
    return dict(action='edit', virtualdir=cfg.wiki_virtdir, page=page, title=title, wikitext=wikitext, errmsg=errmsg)

@app.route('/<page>/edit', method='POST')
def save(page=None):
    if page is None:
        page = 'FrontPage'
        redirect('/%s' % page)
    wikipage = WikiPage(page)
    # print("Saving", page)
    newtext = request.forms.get('newtext')
    wikipage.savewikitext(newtext)
    redirect('%s/%s' % (cfg.wiki_virtdir, page))

@app.route('/search')
@view('wikisearch.mako',output_encoding='utf-8')
def searchform():
    return dict(action='show', virtualdir=cfg.wiki_virtdir, page='Search', title='', searchtext='', searchhint='Enter search criteria', wikihtml='', errmsg='', breadcrumbs='')


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
        \n___Text matches (count)___\n * %s
        ''' % (searchtext, '\n * '.join([i[0] for i in titlehits if i[1]]) or '[None]',
               '\n * '.join(['%s (%s)' % (i[1], i[0]) for i in texthits if i[0]]) or '[None]')
        wikiparser = WikiParser(virtualdir=cfg.wiki_virtdir)
        wikihtml = wikiparser("SearchResults",wikitext)
    return dict(action='show', virtualdir=cfg.wiki_virtdir, page='Search', title='', searchtext=searchtext, searchhint='', wikihtml=wikihtml, errmsg='', breadcrumbs='')

re_findwikiname= re.compile(r'([A-Z]+[a-z]+-*[_A-Z0-9][_A-Za-z0-9]+)')
@app.route('/sitemap')
@view('wikishow.mako',output_encoding='utf-8')
def sitemap(top_page='FrontPage'):
    def mapchildren(page, indent, wikitext=''):
        # print >> sys.stderr, 'Inspecting', page
        pagechildren = re_findwikiname.findall(WikiPage(page).getwikitext())
        # print >> sys.stderr, 'page children', pagechildren
        # print >> sys.stderr, 'wikitext at start of inspection:\n',wikitext
        for child in pagechildren:
            if child in existingpages:
                wikitext += '%s* %s\n' %(' ' * indent, child)
                if child not in mappedpages:
                    unmappedpages.remove(child)
                    mappedpages.append(child)
                    wikitext = mapchildren(child, indent + 1, wikitext=wikitext)
            elif child not in wantedpages:
                wantedpages.append((child,page))
        return wikitext
    wantedpages = []
    mappedpages = []
    existingpages = [i for i in getwikipagelist() if i != top_page]
    unmappedpages = existingpages[:]
    # print >> sys.stderr, existingpages
    wikitext = '__Main tree of pages, starting from %s__\n * %s\n' % (top_page,top_page)
    wikitext = mapchildren(top_page, 2, wikitext=wikitext)
    # print >> sys.stderr, wikitext
    # print >> sys.stderr, mappedpages
    # print >> sys.stderr, unmappedpages
    # print >> sys.stderr, wantedpages


    # backsearch
    p = re.compile(r'\b%s\b' % top_page)
    referers = [i for i in getwikipagelist() if p.search(WikiPage(i).getwikitext())]
    referers.sort()
    # wikitext += "__Pages referring to '%s'__\n *%s" % (self.wikipage.title, '\n *'.join(referers) or '[None]') + '\n'
    wikitext += "__Pages referring to '%s'__\n *%s" % (top_page, '\n *'.join(referers) or '[None]') + '\n'

    unmappedpages.sort()
    wikitext += '__Pages outside main tree__\n *' \
                        + ('\n *'.join(unmappedpages) or '[None]') + '\n'
    wantedpages.sort()
    wikitext += '__Pages that are referenced but do not exist:__\n *' \
                        + ('\n *'.join(['%s ? %s' % i for i in wantedpages]) or '[None]') + '\n'
    wikiparser = WikiParser(virtualdir=cfg.wiki_virtdir)
    wikihtml = wikiparser("SiteMap",wikitext)
    return dict(action='show', virtualdir=cfg.wiki_virtdir, page='Site Map', title='Site Map', wikihtml=wikihtml, errmsg='', breadcrumbs='')
