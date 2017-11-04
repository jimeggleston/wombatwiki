#!py27
import bottle
from bottle import mako_view as view
from bottle import static_file, request, redirect, hook
import beaker.middleware
import re
import os,sys
import cgi
import interwiki, emoticons

bottle.debug(True)
root = "/home/jeggles/mysite"
sys.path.insert(0,root)
staticroot = root + "/static"
pageroot = root + "/pages"
sessionroot = root + "/sessions"
cacheroot = root + "/cache"
bottle.TEMPLATE_PATH.insert(0,root + "/views/")
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.data_dir': sessionroot,
    'session.auto': True
}
app = bottle.app()
wrapperapp = beaker.middleware.SessionMiddleware(app, session_opts)


"""
#==CONFIGURATION SECTION===========================================================================
PYTHON_LIB = '/home/jeggles/public_html/wombatwiki/lib'  # local to the web server!
PATH_TO_WIKI_TEXT = '/home/jeggles/public_html/wombatwiki/data/'
PATH_TO_HTML_TEXT = '/home/jeggles/public_html'
PATH_TO_TEMPLATES = '/home/jeggles/public_html/wombatwiki/templates/'
AUTH_SCRIPT = '/wombatwiki/ww.cgi'
AUTH_ACTIONS = ('edit','rename','delete')
FRONT_PAGE = 'FrontPage' #required, must be WikiName. (= name of 'top' or 'home' page)
EXCLUDED_LINKS = ['ListFields']     # Don't display these in the footer
NOFOLLOW_OUTLINKS = 1
REWRITE_MODE = 2
REWRITE_BASE_URL = '/'
DEBUG_ON = 1
EDITABLE = 1
BACKUP_ON = 0 #use the backup feature? (backups will be done in a backup directory)
MAIL_NOTIFICATION_ON = 0   # future: send a modified page list to a notification list
SMTP_SERVER = 'localhost'
WIKI_LOGGER = 'wikilogger@your.domain' #email address from which backups are sent
WIKI_MASTER = 'wikimaster@your.domain' #email address to which backups are sent
#==================================================================================================
"""
NOFOLLOW_OUTLINKS = 1


EMPH_RE = re.compile(
    r'(?P<nowiki1>\{\{\{.*?\}\}\})'
    + r'|(?P<emph>\'{2,3})'
    + r'|(?P<bold>\*\*.*?\*\*)'
    + r'|(?P<code>\{\{.*?\}\})'
    )    

#    + r'|(?P<toc>&lt;TableOfContents.*?&gt;)'

MAIN_RE = re.compile(
    r'(?P<nowiki2>\{\{\{.*?\}\}\})'
    + r'|(?P<toc>\<TableOfContents.*?\>)'
    + r'|(?P<para>\n\s*$)'
    + r'|(?P<list>\n\s+[*#]\s+?)'
    + r'|(?P<heading>\n[=_]{1,6}.+[=_]{1,6}\s*$)'
    + r'|(?P<std_line_start>^\n)'
    #+ r'|(?P<brcm>\n?\\{2})'
    + r'|(?P<rule>\n?-{4,})'
    + r'|(?P<sformat>\{{2,}|\}{2,})'
    + r'|(?P<comment>\[\[.*?\]\])'
    + r'|\[(?P<link>(http|https|ftp|nntp|news|file)\:[^\s]+\s+[^]]+)\]'
    + r'|\[(?P<interwiki>\w+?;.*?;.*)\]'
    + r'|\[(?P<wikilink>(?:[A-Z]+[a-z]+-*[_A-Z0-9][_A-Za-z0-9]+)\s+[^\]]+)\]'
    + r'|(?P<wiki>\b(?:[A-Z]+[a-z]+-*[_A-Z0-9][_A-Za-z0-9]+)\b)'
    + r'|(?P<image>\bimg[lcr]?:\S*\b)'
    + r'|(?P<url>(http|https|ftp|nntp|news|file)\:[^\s\'"]+)'
    + r'|(?P<www>www\.[^\s\'"]+)'
    + r'|(?P<email>(mailto:)?[-\w.+]+@[a-zA-Z0-9\-.]+)'
    + r'|(?P<break>&lt;br&gt;)'
    + r'|(?P<emoticon>[\(\/][A-Z8\;\:\-\|\(\)\*\@]{1,3}[\)\\])'
    )

#~ # Save this for later
#~ interwikiprompt = '''
#~ <script language="javascript" type="text/javascript" charset="ISO-8859-1"><!--
    #~ function ask(pURL) {
        #~ var x = prompt("Enter the word you're searching for:", "");
        #~ if (x != null) {
            #~ var pos = pURL.indexOf("$1");
            #~ if (pos > 0) {
                #~ top.location.assign(pURL.substring(0, pos) + x + pURL.substring(pos + 2, pURL.length));
            #~ } else {
                #~ top.location.assign(pURL + x);
            #~ }
        #~ }
    #~ }
#~ //--></script>
#~ '''


# Error handling helper function
def eh():
    html = '<hr><pre>'
    html += '\r\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
    html += '</pre>'
    return html

def dbgprt(*items):
    text = ' '.join([str(i) for i in items])
    print '<pre>%s</pre><br>' % text     

def formatwikiname(name):
    return re.sub('([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ')


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
        

class WikiParser(object):
    def __init__(self):
        self.emph_re = EMPH_RE
        self.main_re = MAIN_RE
        self.toggles = {'i': 0, 'b': 0, 'pre': 0, 'nowiki': 0}
                
    #all methods in the form _*_repl are helpers for replace, substituting wiki markup tokens
    #with appropriate HTML tags 
    def _sformat_repl(self, s):
        "for special formatting: either 'preformatted text', or 'no wiki translation'"
        r=''
        if '{' in s:
            if len(s) not in (3,4) and not self.toggles['pre']:
                r += '<pre>'
                self.toggles['pre'] = 1
                s = s[2:]
            if len(s) >= 3 and not self.toggles['nowiki']:
                r += '<nowiki>' #yes I know there's no such tag, but it's useful to see!
                self.toggles['nowiki'] = 1
                s = s[3:]
        else:
            if len(s) >= 3 and self.toggles['nowiki']:
                r += '</nowiki>'
                self.toggles['nowiki'] = 0
                s = s[3:]
            if len(s) >=2 and self.toggles['pre']:
                r += '</pre>'
                self.toggles['pre'] = 0
                s = s[2:]
        return r + s

    def _code_repl(self, s):
        return '<code>%s</code>' % s[2:-2]

    def _nowiki1_repl(self, s):
        return s

    def _nowiki2_repl(self, s):
        return '<nowiki>%s</nowiki>' % s[3:-3]

    def _comment_repl(self, s):
        if s.count('--'):   #likely to be invalid comment
            return s
        else:
            return '<!--%s-->' % s[2:-2]
    
    def _toc_repl(self, s):
        self.toc_requested = 1
        m = re.search(r':([0-9]+),*([0-9]*)&gt;', s)
        if m is not None: 
            self.toc_minlevel = int(m.groups(0)[0])
            if m.groups(0)[1] == '':
                self.toc_maxlevel = self.toc_minlevel
            else:
                self.toc_maxlevel = int(m.groups(0)[1])
        return '<TableOfContents>'

    def _heading_repl(self, s):
        m = re.search(r'([=_]{1,6})(.+)\1', s)  #refine resolution of heading
        if m:
            hlevel = len(m.group(1))
            hcount = len(self.headings) + 1
            text = m.group(2)
            self.headings.append((hcount, hlevel, text))
            return self.dedent() + '\n<a name="h%s"><h%s>%s</h%s></a>\r' % (hcount, hlevel, text, hlevel)
        else:
            return s
    
    def _para_repl(self, s):
        if self.toggles['pre']:
            return '\n\r'
        else:
            return self.dedent() + '\n<p>\r'

    def _brcm_repl(self, s):
        return '\n<br clear="all">\r'
        
    def _emph_repl(self, s):
        if len(s) == 3:
            self.toggles['b'] = not self.toggles['b']
            return ('</b>', '<b>')[self.toggles['b']]
        else:
            self.toggles['i'] = not self.toggles['i']
            return ('</i>', '<i>')[self.toggles['i']]

    def _bold_repl(self, s):
        return '<b>%s</b>' % s[2:-2]

    def _italic_repl(self, s):
        return '<i>%s</i>' % s[2:-2]

    def _wiki_repl(self, s):
        return '<a class="wiki" href="/%s">%s</a>' % (s, formatwikiname(s))

    def _rule_repl(self, s):
        size = s.count('-') - 3
        if size > 8: size = 8
        return '\n<hr size=%s>\r' % size
    
    def _image_repl(self, s):
        r = '<img src="%s"' % s.split(':', 1)[1]
        if s[3] == 'l':
            r += ' align="left"'
        elif s[3] == 'r':
            r += ' align="right"'
        r += ' />'
        if s[3] == 'c':
            r = '\n<p align="center">%s</p>\r' % r
        return r

    def _url_repl(self, s):
        rel = ('', ' rel="nofollow"')[NOFOLLOW_OUTLINKS]
        return '<a class="external" target="external" href="%s"%s>%s</a>' % (s, rel, s)

    def _link_repl(self, s):
        rel = ('', ' rel="nofollow"')[NOFOLLOW_OUTLINKS]
        h, a = s.split(' ', 1)
        return '<a class="external" target="external" href="%s"%s>%s</a>' % (h, rel, a)

    def _wikilink_repl(self, s):
        h, a = s.split(' ', 1)
        #w = WikiPage(h)
        return '<a class="wiki" href="/%s">%s</a>' % (h, a)
        #if w.existcode:
        #    return '<a class="wiki" href="%s">%s</a>' % (w.get_href(), a)
        #else:
        #    return '[%s<a class="nonexistent" href="%s">?</a> %s]' % (h, w.get_href(), a)

    def _interwiki_repl(self, s):
        parts = s.split(';')
        i = parts[0]
        a = parts[-1]
        p = tuple(parts[1:-1])
        if interwiki.interwiki.has_key(i):
            h = interwiki.interwiki[i] % p
            return '<a class="wikilink" href="%s">%s</a>' % (h, a)
        else:
            return '[%s]' % s

    def _www_repl(self, s):
        return self._url_repl('http://' + s)

    def _email_repl(self, s):
        if s[:7] == 'mailto:':
            href = s
        else:
            href = 'mailto:' + s
        return '<a href="%s">%s</a>' % (href, s)

    def _list_repl(self, s):
        if self.toggles['pre']: return s
        
        s = s[1:].rstrip()
        listtype, itemtag, indent = {'*': ('ul', '<li>', len(s) - 1),
                                     '#': ('ol', '<li>', len(s) - 1)}.get(
                                    s[-1],('blockquote', '<br>', len(s)))
        oldlistlevel = len(self.listqueue)            
        r = ''        
        for i in range(indent, oldlistlevel):#if indent<oldlistlevel
            r += '\n%s</%s>\r' % (' ' * i, self.listqueue.pop())
        for i in range(oldlistlevel, indent):#if indent>oldlistlevel
            r += '\n%s<%s>\r' % (' ' * i, listtype); self.listqueue.append(listtype)
        if listtype != self.listqueue[-1]:#same indent but different flavour list
            r += '\n%s</%s>%s<%s>\r' % (' ' * indent, self.listqueue.pop(), ' ' * indent, listtype)
            self.listqueue.append(listtype)
        r += '\n' + ' ' * indent + itemtag
        return r

    def _std_line_start_repl(self, s):
        if self.toggles['pre']:
            r = '\n'
        else:
            r = self.dedent()
        return r

    def _break_repl(self, s):
        return '<br>'

    def _emoticon_repl(self, s):
        r = s
        i = emoticons.emoticon_image(s)
        if i is not None:
            r = '<img src="%s/%s" %s>' %  ('icons', i,  emoticons.img_properties)
        return r

    def dedent(self):
        'closes lists when required'
        r = ''
        while self.listqueue:
            r += '\n' + ' ' * (len(self.listqueue)-1) + '</%s>\r' % self.listqueue.pop()
        return r

    def togglesoff(self):
        'closes b,i,pre and nowiki tags in case the user has not defined closing tags'
        r = ''
        for k, v in self.toggles.items():
            if v:
                r += '</%s>' % k
                self.toggles[k] = 0
        return r

    def replace(self, match):
        'calls appropriate helper (based on named RE group) to replace each type of token'
        tokentype = match.lastgroup
        token = match.groupdict()[tokentype]
        if self.toggles['nowiki'] and token[:3] != '}}}':
            return token
        else:
            return getattr(self, '_' + tokentype + '_repl')(token)

    def __call__(self, page, text, clearmargins=0):
        'main HTML formatter function'
        if text is None:
            return None
        if not text.strip(): return ''

        self.listqueue = []
        self.headings = []
        self.toc_requested = 0
        self.toc_minlevel = 1
        self.toc_maxlevel = 9999

        #text = cgi.escape(text, 1)
        
        intable = 0
        html = '\r'
        n = 0
        for line in text.splitlines():
            new_html = '\n' + line
            new_html = re.sub(self.emph_re, self.replace, new_html)
            new_html = re.sub(self.emph_re, self.replace, new_html)
            new_html = re.sub(self.main_re, self.replace, new_html)
            # Table processing
            sym = line[:2]
            if sym in ("||", "!!") :
                if not intable:
                    intable = 1
                    if sym == "||":
                        html += '<table border="1" cellspacing="0">\n'
                    else:
                        html += '<table border="0" cellspacing="0">\n'
            else:
                if intable:
                    html +=  "\n</table>\n"
                    intable = 0
            if intable:
                tag1 = '<td valign="top">'
                tag2 = "</td>"
                #~ if sym == "!!": 
                    #~ tag1 = "<th>"
                    #~ tag2 = "</th>"
                cells = ('&nbsp;%s%s' % (tag2, tag1)).join(new_html.split(sym)[1:-1])
                new_html = '<tr>%s%s&nbsp;%s</tr>\n' % (tag1, cells, tag2)
            boundary = html[-1] + new_html[0]
            if '\r' not in boundary and '\n' not in boundary:
                html += '<br>\r\n'       
            html += new_html
        
        if intable: html +=  "</table>"
        
        if self.toc_requested:
            toc = '\n<ul>\n'
            minl = min([l for c,l,h in self.headings])
            lastl = minl
            for c,l,h in self.headings:
                if self.toc_minlevel <= l <= self.toc_maxlevel:
                    if l > lastl: toc += '\n<ul>\n'
                    if l < lastl: toc += '\n</ul>\n'
                    lastl = l
                    toc +=  '<li><a href="#h%s">%s</a></li>\n' % (c,h)
            for l in range(lastl, minl-1, -1):
                toc += '</ul>\n'
            
            html = html.replace('<TableOfContents>', toc)
            
        html += self.togglesoff() + self.dedent()
        if clearmargins: html += '<br clear="all">'
        html = html.replace('\r\n', '\n'); html = html.replace('\r', '\n')
        return html


def processvisited(visited, page, default='FrontPage'):
    if not visited:
        visited = [default]
    if page not in visited:
        visited.append(page)
    else:
        visited = visited[0:visited.index(page)+1]
    if len(visited) > 5:
        visited = [default] + visited[-4:]
    return visited

def formatbreadcrumbs(pages):
    return ' &gt; '.join(['<a href="/%s">%s</a>' % (page, page) for page in pages])


class WikiPage(object):
    pageroot = pageroot
    def __init__(self, page,pagecache=MemCache()):
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
            self.wikihtml = self.wikiparser(self.page,self.getwikitext())
        self.pagecache.update(self.page, self.wikihtml)
        return self.wikihtml

def getwikipagelist(pageroot=pageroot):
    pages = os.listdir(pageroot)
    pages.sort()
    return pages

@hook('before_request')
def setup_request():
    request.session = request.environ['beaker.session']

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
        errmsg = '%s not found.' % page
        page = "FrontPage"
        wikipage = WikiPage(page)
        wikihtml = wikipage.getwikihtml()
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
    wikitext = wikipage.getwikitext()
    errmsg = ''
    if wikitext is None:
        errmsg = '%s not found.' % page
        page = "FrontPage"
        pagefile = os.path.join(pageroot, page)
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

@app.route('/search', method='POST')
@view('wikishow.mako',output_encoding='utf-8')
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
    return dict(action='show', page='Search', title='Search', searchtext=searchtext, wikihtml=wikihtml, errmsg='', breadcrumbs='')


bottle.run(app=wrapperapp, host='localhost', port=80, server="tornado")
