import os,sys

# Are we running in a dev (local PC) or prod (hosted) environment
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

# Bottle paths
staticroot = root + "/static"
pageroot = root + "/pages"
sessionroot = root + "/sessions"
cacheroot = root + "/cache"
libroot = root + "/lib"
viewroot = root + "/views"

# URL virtual directories
wiki_virtdir = '/wiki'

# Beaker middleware variables
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.data_dir': sessionroot,
    'session.auto': True
}

# Put the app-specific python lib path on the python path
sys.path.insert(0,libroot)