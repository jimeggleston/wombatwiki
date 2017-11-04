<%inherit file="base.mako" />
<div class="body" ondblclick="location.href='/${page}/edit'">
    ${wikihtml.decode('UTF-8','replace')}
</div>
