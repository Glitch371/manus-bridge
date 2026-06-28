# ManusBridge - Ponte HTTP tra Manus AI e Blender 3D
# Copyright (C) 2026 Glitch371
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "ManusBridge",
    "author": "Manus AI",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Manus",
    "description": "Ponte diretto tra Manus AI e Blender per automazione",
    "category": "Automation",
    "license": "SPDX:GPL-3.0-or-later",
}

import bpy
import threading
import json
import queue
from http.server import BaseHTTPRequestHandler, HTTPServer

server_thread = None

# Queue used to pass commands from the HTTP thread to Blender's main thread
_command_queue = queue.Queue()


def _process_command_queue():
    """Timer callback that runs in Blender's main thread to drain the queue."""
    while not _command_queue.empty():
        cmd, result_holder, event = _command_queue.get_nowait()
        try:
            exec_globals = {"bpy": bpy, "json": json}
            exec(cmd, exec_globals)
            result_holder["status"] = "success"
            result_holder["message"] = "Comando eseguito"
        except Exception as e:
            result_holder["status"] = "error"
            result_holder["message"] = str(e)
        finally:
            event.set()
    return 0.1  # re-schedule every 100 ms


class ManusHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        command = data.get("command", "")
        print(f"ManusBridge: Esecuzione comando -> {command}")

        # Hand the command to Blender's main thread and wait for the result
        result_holder = {}
        done_event = threading.Event()
        _command_queue.put((command, result_holder, done_event))
        done_event.wait(timeout=30)

        if not done_event.is_set():
            result_holder = {"status": "error", "message": "Timeout: comando non eseguito"}

        status_code = 200 if result_holder.get("status") == "success" else 500
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result_holder).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"ManusBridge is active!")

    def log_message(self, format, *args):
        # Suppress default access log spam in Blender's console
        pass


def run_server():
    server_address = ('', 9999)
    httpd = HTTPServer(server_address, ManusHandler)
    print("ManusBridge: Server avviato sulla porta 9999")
    httpd.serve_forever()


class MANUS_OT_StartServer(bpy.types.Operator):
    bl_idname = "manus.start_server"
    bl_label = "Avvia ManusBridge"

    def execute(self, context):
        global server_thread
        if server_thread is None or not server_thread.is_alive():
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            if not bpy.app.timers.is_registered(_process_command_queue):
                bpy.app.timers.register(_process_command_queue, persistent=True)
            self.report({'INFO'}, "ManusBridge Avviato su porta 9999")
        else:
            self.report({'WARNING'}, "ManusBridge è già in esecuzione")
        return {'FINISHED'}


class MANUS_PT_Panel(bpy.types.Panel):
    bl_label = "Manus AI Bridge"
    bl_idname = "MANUS_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Manus'

    def draw(self, context):
        layout = self.layout
        layout.operator("manus.start_server", icon='PLAY')

        global server_thread
        if server_thread and server_thread.is_alive():
            layout.label(text="Stato: Connesso (Porta 9999)", icon='CHECKMARK')
        else:
            layout.label(text="Stato: Disconnesso", icon='CANCEL')


def register():
    bpy.utils.register_class(MANUS_OT_StartServer)
    bpy.utils.register_class(MANUS_PT_Panel)


def unregister():
    if bpy.app.timers.is_registered(_process_command_queue):
        bpy.app.timers.unregister(_process_command_queue)
    bpy.utils.unregister_class(MANUS_PT_Panel)
    bpy.utils.unregister_class(MANUS_OT_StartServer)


if __name__ == "__main__":
    register()
