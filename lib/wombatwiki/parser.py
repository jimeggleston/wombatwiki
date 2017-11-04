#!python
import re
import emoticons, interwiki

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


def formatwikiname(name):
    return re.sub('([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ')


class WikiParser(object):
    def __init__(self,virtualdir=''):
        self.virtualdir = virtualdir
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
            return self.dedent() + '\n<p />\r'

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
        return '<a class="wiki" href="%s/%s">%s</a>' % (self.virtualdir, s, formatwikiname(s))

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

def formatbreadcrumbs(pages, virtualdir=''):
    return ' &gt; '.join(['<a href="%s/%s">%s</a>' % (virtualdir, page, page) for page in pages])

