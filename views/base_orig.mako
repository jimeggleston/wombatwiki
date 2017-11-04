## -*- coding: utf-8 -*-
<!DOCTYPE HTML>
<html lang="EN">
    <head>
        <title>${title}</title>
        <meta name="description" CONTENT="">
        <meta name="keywords" CONTENT="">
        <link href='/css/entireframework.min.css' rel='stylesheet'>
        <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon" -->
    </head>
    <%block name="top">
    <body>
        %if errmsg:
            <div class="error">
                ${errmsg}
            </div>
        %endif
    </%block>
    
    <div class="header">
        <%block name="header">
            <h1>${title}</h1>
        </%block>
    </div>

    ${self.content()}

    <div class="footer">
    <%block name="footer">
        <p>
        %if page!="FrontPage":
            [<a href="/FrontPage">Front Page</a>]
        %endif
        </p>
    </%block>
    </div>
    </body>
</html>