from flask_socketio import SocketIO, join_room

socketio = SocketIO(cors_allowed_origins="*", logger=True)


@socketio.on("join")
def on_join(room):
    join_room(room)
