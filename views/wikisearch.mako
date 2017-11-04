<%inherit file="base.mako" />
<%block name="top">
    <nav class="nav" tabindex="-1" onclick="this.focus()">
        <a class="pagename current" href="/">JEGGLES</a>
        <a href="${virtualdir}/search">Search</a>
    </nav>
    <p>
        ${breadcrumbs}
    </p>
    <p>
        ${errmsg}
    </p>
    <form method="post" action="${virtualdir}/search" border="0">
        <span class="addon"><input type="text" name="searchtext" value="${searchtext}" placeholder="${searchhint}" size="80"><input type="submit" value="Search"></span>
    </form>
</%block>

<%block name="content">
    <div class="container">
        ${wikihtml.decode('UTF-8','replace')}
    </div>
</%block>


