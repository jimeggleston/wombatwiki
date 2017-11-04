img_properties = 'width="14" height="12" alt=""'
valid_letters = 'YNLUKGFPBDTCIHS8EM'
emoticons = {
    "(:-)" : "emoticon-smile.gif",
    "(;-)" : "emoticon-wink.gif",
    "(:-()" : "emoticon-sad.gif",
    "(:-|)" : "emoticon-ambivalent.gif",
    "(:-D)" : "emoticon-laugh.gif",
    "(:-O)" : "emoticon-surprised.gif",
    "(:-P)" : "emoticon-tongue-in-cheek.gif",
    "(:-S)" : "emoticon-unsure.gif",
    "(*)"   : "emoticon-star.gif",
    "(@)"   : "emoticon-cat.gif",
    "/I\\"   : "icon-info.gif",
    "/W\\"   : "icon-warning.gif",
    "/S\\"   : "icon-error.gif"
}
def emoticon_image(txt):
    if emoticons.has_key(txt): return emoticons[txt]
    txt = txt[1:-1]
    if valid_letters.find(txt) >= 0: return "emoticon-%s.gif" % txt
    return None
