#!/usr/bin/env python3
"""Tiny static server WITH HTTP Range support.

python -m http.server does not implement Range, so <audio> cannot seek or
stream properly. Binds to 127.0.0.1 by default -- nothing leaves this machine.

Pass --lan to bind all interfaces so a phone or iPad on the same wifi can reach
it. That exposes this folder, read-only, to everyone on your local network for
as long as it runs, so use it to test on a device and then stop it.
"""
import http.server, os, re, socket, socketserver, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()

        m = re.match(r'bytes=(\d*)-(\d*)', rng.strip())
        if not m:
            return super().do_GET()

        size = os.path.getsize(path)
        s, e = m.group(1), m.group(2)
        if s == '':                               # suffix range: last N bytes
            start, end = max(0, size - int(e)), size - 1
        else:
            start = int(s)
            end = int(e) if e else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return

        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return                        # browser closed the stream
                remaining -= len(chunk)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.0.2.1', 1))       # never sends: just picks the route
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    lan = '--lan' in sys.argv
    port = int(args[0]) if args else 8800
    host = '0.0.0.0' if lan else '127.0.0.1'
    with Server((host, port), Handler) as httpd:
        if lan:
            print(f'serving {ROOT}')
            print(f'  this mac : http://127.0.0.1:{port}/index.html')
            print(f'  phone    : http://{lan_ip()}:{port}/index.html')
            print('  (open to your local network while running - ctrl-c to stop)')
        else:
            print(f'serving {ROOT} on http://127.0.0.1:{port}/index.html')
        httpd.serve_forever()
