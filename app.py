#!py27
from bottle import Bottle
from bottle import mako_view as view
from bottle import static_file

staticroot = "b:/websites/bottle/static"

app = Bottle()

@app.route('/<filename:re:.*\..*>')
def send_file(filename):
    return static_file(filename, root=staticroot)

@app.route('/hello')
@app.route('/hello/')
@app.route('/hello/<name>')
@view('hello_template.mako')
def hello(name='World'):
    return dict(name=name, platform="Bottle")

app.run(host='localhost', port=80, server='tornado', debug=True)
