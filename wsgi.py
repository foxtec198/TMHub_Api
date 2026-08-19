from gevent import monkey; monkey.patch_all()  # Importante manter em primeira instancia
from app import socketio, app

if __name__ == "__main__": socketio.run(app)
