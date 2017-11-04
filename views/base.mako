## -*- coding: utf-8 -*-
<!DOCTYPE HTML>
<html lang="EN">
    <head>
        <title>JEGGLES</title>
        <meta name="description" CONTENT="">
        <meta name="keywords" CONTENT="">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="/css/entireframework.min.css" rel="stylesheet">
        <!-- link href="//mincss.com/entireframework.min.css" rel="stylesheet" -->
        <link href="/css/overlay.min.css" rel="stylesheet">
        <!-- link rel="shortcut icon" href="/favicon.ico" type="image/x-icon" -->
    </head>
    <div name="top">
    <%block name="top">
    <body>
        <nav class="nav" tabindex="-1" onclick="this.focus()">
            <div class="container">
                <a class="pagename current" href="/">JEGGLES</a>
            </div>
		</nav>
        %if errmsg:
            <div class="error">
                ${errmsg}
            </div>
        %endif
    </%block>
    </div>

    <div class="header">
    <%block name="header">
        <h2>${title}</h2>
    </%block>
    </div>

    <div class="content">
    <%block name="content">
        ${self.content()}
    </%block>
    </div>

    <div class="footer">
    <%block name="footer">
    </%block>
    </div>
    </body>
</html>