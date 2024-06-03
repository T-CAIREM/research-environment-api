from flask_socketio import SocketIO, join_room

socketio = SocketIO(cors_allowed_origins="*", logger=True, ping_interval=25, ping_timeout=60)


@socketio.on("join")
def on_join(room):
    join_room(room)
