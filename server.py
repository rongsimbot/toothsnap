from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir('/home/simrobotics/toothsnap_demo')

class MyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

print('ToothSnap Demo Server running on http://192.168.1.139:8080')
HTTPServer(('0.0.0.0', 8080), MyHandler).serve_forever()
