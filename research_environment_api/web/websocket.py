from flask_socketio import SocketIO, join_room
from os import environ

socketio = SocketIO(
    cors_allowed_origins="*", logger=True
)


@socketio.on("join")
def on_join(room):
    join_room(room)
