import os
runtime_env = "PROD"
try:
    if os.environ['USERDOMAIN'].upper() == 'TOSHIBALAPTOP':
        runtime_env = "DEV"
except:
    pass
if runtime_env == "DEV" :
    print "DEVELOPMENT ENVIRONMENT"
    root = "./"
else:
    print "PRODUCTION ENVIRONMENT"
    root = "/home/jeggles/mysite"

staticroot = root + "/static"
pageroot = root + "/pages"
sessionroot = root + "/sessions"
cacheroot = root + "/cache"
libroot = root + "/lib"
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.data_dir': sessionroot,
    'session.auto': True
}