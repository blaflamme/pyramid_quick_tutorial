from os import getcwd

from pyramid.config import Configurator
from pyramid.events import NewRequest, ApplicationCreated
from pyramid.httpexceptions import HTTPFound
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.view import view_config

from paste.httpserver import serve
import sqlite3

# views
@view_config(route_name='list', renderer='list.mako')
def list(request):
    rs = request.db.execute("select id, name from tasks where closed = 0")
    tasks = [dict(id=row[0], name=row[1]) for row in rs.fetchall()]
    return {'tasks': tasks}

@view_config(route_name='new', renderer='new.mako')
def new(request):
    if request.method == 'POST':
        if request.params.get('name'):
            request.db.execute('insert into tasks (name, closed) values (?, ?)',
                               [request.params['name'], 0])
            request.db.commit()
            request.session.flash('New task was successfully added!')
            return HTTPFound(location=request.route_url('list'))
        else:
            request.session.flash('Please enter a name for the task!')
    return {}

@view_config(route_name='close')
def close(request):
    task_id = int(request.matchdict['id'])
    request.db.execute("update tasks set closed = ? where id = ?", (1, task_id))
    request.db.commit()
    request.session.flash('Task was successfully closed!')
    return HTTPFound(location=request.route_url('list'))

# subscribers
def add_subscribers(event):
    request = event.request
    open_db_connection(request)
    request.add_finished_callback(close_db_connection)

def open_db_connection(request):
    settings = request.registry.settings
    request.db = sqlite3.connect(settings['db'])

def close_db_connection(request):
    request.db.close()
    
def db_init(app):
    print 'Initializing database...'
    f = open('schema.sql', 'r')
    stmt = f.read()
    settings = app.app.registry.settings
    db = sqlite3.connect(settings['db'])
    db.executescript(stmt)
    db.commit()
    f.close()

if __name__ == '__main__':
    # configuration settings
    settings = {}
    settings['reload_all'] = True
    settings['debug_all'] = True
    settings['mako.directories'] = '.'
    settings['db'] = 'tasks.db'
    # session factory
    session_factory = UnencryptedCookieSessionFactoryConfig('itsaseekreet')
    # configuration setup
    config = Configurator(settings=settings, session_factory=session_factory)
    # subscribers
    config.add_subscriber(add_subscribers, NewRequest)
    config.add_subscriber(db_init, ApplicationCreated)
    # routes setup
    config.add_route('list', '/')
    config.add_route('new', '/new')
    config.add_route('close', '/close/{id}')
    # static view setup
    config.add_static_view('static', getcwd()+'/static')
    # 
    config.scan()
    # serve app
    app = config.make_wsgi_app()
    serve(app, host='0.0.0.0')
