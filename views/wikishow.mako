<%inherit file="base.mako" />

<%block name="top">
<body ondblclick="location.href='${virtualdir}/${page}/edit'">
    <nav class="nav" tabindex="-1" onclick="this.focus()">
        <div class="container">
            <a class="pagename current" href="/">JEGGLES</a>
            <a href="${virtualdir}/search">Search</a>
            <a href="${virtualdir}/sitemap">Site Map</a>
            <a href="${virtualdir}/${page}/edit">Edit</a>
            <a href="${virtualdir}/WikiHelp">Help</a>
        </div>
    </nav>
    <button class="btn-close btn btn-sm">×</button>
    <p>
        ${breadcrumbs}
    </p>
    <p>
        ${errmsg}
    </p>
</%block>

<%block name="content">
    <div class="container">
        ${wikihtml.decode('UTF-8','replace')}
    </div>
</%block>
