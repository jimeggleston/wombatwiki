<%inherit file="base.mako" />
<%block name="content">
<div class="content" width="1024">
    <form method="post" action="${virtualdir}/${page}/edit">
        <textarea class="edit" name="newtext" rows="20" cols="1024">${wikitext.decode('UTF-8','replace')}</textarea>
        <br>
        <span class="addon" border="0"><input type=submit value="Save" name="save"> <input type=reset value="Reset"></span>
    </form>
</div>
</%block>

