from flask_socketio import SocketIO, join_room, leave_room, rooms
from flask import request

socketio = SocketIO(
    cors_allowed_origins="*", logger=True, ping_interval=25, ping_timeout=60
)


@socketio.on("join")
def on_join(room):
    socket_id = request.sid
    socket_rooms = rooms(sid=socket_id)
    if room not in socket_rooms:
        join_room(room, sid=socket_id)


@socketio.on("disconnect")
def on_disconnect():
    socket_id = request.sid
    socket_rooms = rooms(sid=socket_id)
    for room in socket_rooms:
        leave_room(room, sid=socket_id)
