@echo off
cd /d "D:\AI大模型RAG与智能体开发_Agent项目"
set PYTHONPATH=D:\AI大模型RAG与智能体开发_Agent项目
set DASHSCOPE_API_KEY=sk-e0dd94d3699b4d23a81bcb1a50d465e0
set JWT_SECRET_KEY=dev-secret-key-change-in-production
start "Backend" /MIN D:\anaconde\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000
timeout /t 8 /nobreak >nul
start "Frontend" /MIN D:\anaconde\python.exe -c "import os,sys,json,http.server,urllib.request; D=r'D:\AI大模型RAG与智能体开发_Agent项目\frontend\dist'; class H(http.server.SimpleHTTPRequestHandler): directory=D; def do_GET(self): return self._proxy_or_static(); def do_POST(self): return self._proxy() if self.path.startswith('/api/') else self.send_error(405); def do_DELETE(self): return self._proxy() if self.path.startswith('/api/') else self.send_error(405); def _proxy(self): body=self.rfile.read(int(self.headers.get('Content-Length',0))) if self.headers.get('Content-Length') else b''; resp=urllib.request.urlopen(urllib.request.Request('http://localhost:8000'+self.path,data=body or None,method=self.command,headers={'Content-Type':self.headers.get('Content-Type','')})); self.send_response(resp.status); self.send_header('Content-Type',resp.headers.get('Content-Type','application/json')); self.end_headers(); self.wfile.write(resp.read()); return None; def _proxy_or_static(self): return self._proxy() if self.path.startswith('/api/') else (super().do_GET() if os.path.isfile(D+self.path) else (setattr(self,'path','/index.html') or super().do_GET())); def log_message(self,*a): pass
http.server.HTTPServer(('0.0.0.0',3000),H).serve_forever()"
echo All services started.
echo API: http://localhost:8000
echo UI:  http://localhost:3000
