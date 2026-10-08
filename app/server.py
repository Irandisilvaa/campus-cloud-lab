"""Portal didático sem dependências externas. Não é um servidor de produção."""
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
NODE = os.getenv('NODE_NAME', 'Local')
PRIVATE_NAME = 'app.campus.internal'
EVENTS = [
    {'title': 'Semana da Computação', 'category': 'Tecnologia', 'date': 'Dia 12 · 14h', 'place': 'Auditório de Computação', 'description': 'Projetos, pesquisa e conversas sobre o futuro da tecnologia.'},
    {'title': 'Ideias que viram projetos', 'category': 'Inovação', 'date': 'Dia 13 · 16h', 'place': 'Espaço de Inovação', 'description': 'Uma oficina para tirar uma ideia do papel e trabalhar em equipe.'},
    {'title': 'Primeiros passos na nuvem', 'category': 'Workshop', 'date': 'Dia 14 · 09h', 'place': 'Laboratório de Informática', 'description': 'Redes, disponibilidade e segurança aplicadas a um portal real.'},
]

class Handler(BaseHTTPRequestHandler):
    server_version = 'CampusLab/1.0'
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def respond(self, status, body, kind='application/json; charset=utf-8'):
        payload = json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/health':
            return self.respond(200, {'status': 'ok', 'server': NODE})
        if path == '/api/eventos':
            return self.respond(200, {'server': NODE, 'events': EVENTS})
        if path == '/api/status':
            return self.respond(200, {'server': NODE, 'forwarded_protocol': self.headers.get('X-Forwarded-Proto', 'http'), 'note': 'Protocolo informado pelo proxy; não é prova isolada de TLS.'})
        if path == '/api/dns':
            try:
                addresses = sorted({item[4][0] for item in socket.getaddrinfo(PRIVATE_NAME, 8080, family=socket.AF_INET, type=socket.SOCK_STREAM)})
                return self.respond(200, {'name': PRIVATE_NAME, 'addresses': addresses, 'server': NODE, 'origin': 'Consulta realizada pelo servidor, dentro da VPC quando implantado na AWS.'})
            except socket.gaierror:
                return self.respond(503, {'name': PRIVATE_NAME, 'server': NODE, 'error': 'Nome privado ainda não resolve. Crie a stack DNS privado e confira associação com a VPC.'})
        if path == '/admin':
            return self.respond(200, {'message': 'Área fictícia do laboratório. Não contém dados nem ações administrativas. O WAF deve bloquear este caminho após ativação.', 'server': NODE})
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if path in files:
            name, kind = files[path]
            return self.respond(200, (ROOT / name).read_bytes(), kind)
        return self.respond(404, {'error': 'Página não encontrada'})

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '8080'))
    print(f'Campus Lab em http://{host}:{port} — {NODE}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
