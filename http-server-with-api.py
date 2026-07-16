#!/usr/bin/env python3
"""
HTTP Server for VNA SmartWay with integrated Notifications API
Serves static files from D:\Smartway on port 3000
Provides /api/* endpoints for notifications
Run: python http-server-with-api.py
Access: http://localhost:3000
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import mimetypes
from datetime import datetime
import urllib.parse

NOTIFICATIONS_FILE = 'd:/Smartway/notifications-data.json'
BASE_DIR = 'd:/Smartway'

class SmartWayHandler(BaseHTTPRequestHandler):
    def _load_notifications(self):
        """Load notifications from file"""
        try:
            if os.path.exists(NOTIFICATIONS_FILE):
                with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def _save_notifications(self, data):
        """Save notifications to file"""
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _send_json_response(self, status, data):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_file(self, file_path):
        """Send static file"""
        try:
            if os.path.isfile(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                mime_type = mime_type or 'application/octet-stream'
                
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', len(content))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return True
        except:
            pass
        return False
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        print(f"[GET] {self.path}", flush=True)
        # Parse path
        path = urllib.parse.urlparse(self.path).path
        
        # API endpoints
        if path == '/api/notifications':
            notifications = self._load_notifications()
            self._send_json_response(200, notifications)
        
        elif path.startswith('/api/notifications/'):
            pnr = path.split('/')[-1].upper()
            notifications = self._load_notifications()
            pnr_notifications = [n for n in notifications if n.get('pnr') == pnr]
            self._send_json_response(200, pnr_notifications)
        
        else:
            # Serve static files
            if path == '/':
                path = '/admin-manage-notifications.html'
            
            file_path = BASE_DIR + path.replace('/', '\\')
            
            # Prevent directory traversal
            if not os.path.abspath(file_path).startswith(os.path.abspath(BASE_DIR)):
                self.send_response(403)
                self.end_headers()
                return
            
            if self._send_file(file_path):
                return
            
            # Try with index.html
            if os.path.isdir(file_path):
                if self._send_file(file_path + '\\index.html'):
                    return
            
            # 404
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
    
    def do_POST(self):
        """Handle POST requests for creating notifications"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/api/notifications':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                notification = json.loads(body)
                
                # Validation
                if not notification.get('pnr') or not notification.get('title'):
                    self._send_json_response(400, {'error': 'Missing required fields: pnr, title'})
                    return
                
                # Add timestamp
                notification['timestamp'] = int(datetime.now().timestamp() * 1000)
                notification['pnr'] = notification['pnr'].upper()
                
                # Load and save
                notifications = self._load_notifications()
                notifications.append(notification)
                self._save_notifications(notifications)
                
                self._send_json_response(201, {
                    'success': True,
                    'message': f"Notification created for PNR: {notification['pnr']}",
                    'notification': notification
                })
            
            except json.JSONDecodeError:
                self._send_json_response(400, {'error': 'Invalid JSON'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def do_DELETE(self):
        """Handle DELETE requests for removing notifications"""
        path = urllib.parse.urlparse(self.path).path
        
        if path.startswith('/api/notifications/delete/'):
            try:
                notif_id = int(path.split('/')[-1])
                notifications = self._load_notifications()
                
                if 0 <= notif_id < len(notifications):
                    deleted = notifications.pop(notif_id)
                    self._save_notifications(notifications)
                    self._send_json_response(200, {
                        'success': True,
                        'message': 'Notification deleted'
                    })
                else:
                    self._send_json_response(404, {'error': 'Not found'})
            except:
                self._send_json_response(400, {'error': 'Invalid request'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def log_message(self, format, *args):
        """Custom logging"""
        # Log API requests only
        if '/api/' in self.path:
            print(f"[API] {format%args}")

if __name__ == '__main__':
    PORT = 3000
    server = HTTPServer(('0.0.0.0', PORT), SmartWayHandler)
    print(f"🚀 VNA SmartWay HTTP Server with integrated API")
    print(f"   Local: http://localhost:{PORT}")
    print(f"   API: http://localhost:{PORT}/api/notifications")
    print(f"   Files: {BASE_DIR}")
    print(f"\n✅ Server running on port {PORT}")
    print(f"   Access web app: http://localhost:{PORT}/VNA%20SmartWay%20V%201.7.html")
    print(f"   Access admin: http://localhost:{PORT}/admin-manage-notifications.html")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    
    def _load_notifications(self):
        """Load notifications from file"""
        try:
            if os.path.exists(NOTIFICATIONS_FILE):
                with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def _save_notifications(self, data):
        """Save notifications to file"""
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _send_json_response(self, status, data):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/api/notifications':
            # Return all notifications
            notifications = self._load_notifications()
            self._send_json_response(200, notifications)
        
        elif self.path.startswith('/api/notifications/'):
            # Return notifications for specific PNR
            pnr = self.path.split('/')[-1].upper()
            notifications = self._load_notifications()
            pnr_notifications = [n for n in notifications if n.get('pnr') == pnr]
            self._send_json_response(200, pnr_notifications)
        
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for creating notifications"""
        if self.path == '/api/notifications':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                notification = json.loads(body)
                
                # Validation
                if not notification.get('pnr') or not notification.get('title'):
                    self._send_json_response(400, {'error': 'Missing required fields: pnr, title'})
                    return
                
                # Add timestamp
                notification['timestamp'] = int(datetime.now().timestamp() * 1000)
                notification['pnr'] = notification['pnr'].upper()
                
                # Load and save
                notifications = self._load_notifications()
                notifications.append(notification)
                self._save_notifications(notifications)
                
                self._send_json_response(201, {
                    'success': True,
                    'message': f"Notification created for PNR: {notification['pnr']}",
                    'notification': notification
                })
            
            except json.JSONDecodeError:
                self._send_json_response(400, {'error': 'Invalid JSON'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def do_DELETE(self):
        """Handle DELETE requests for removing notifications"""
        if self.path.startswith('/api/notifications/delete/'):
            try:
                notif_id = int(self.path.split('/')[-1])
                notifications = self._load_notifications()
                
                if 0 <= notif_id < len(notifications):
                    deleted = notifications.pop(notif_id)
                    self._save_notifications(notifications)
                    self._send_json_response(200, {
                        'success': True,
                        'message': 'Notification deleted'
                    })
                else:
                    self._send_json_response(404, {'error': 'Not found'})
            except:
                self._send_json_response(400, {'error': 'Invalid request'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def log_message(self, format, *args):
        """Custom logging"""
        # Log API requests, suppress static file logs
        if '/api/' in self.path:
            print(f"[{self.log_date_time_string()}] {format%args}")

if __name__ == '__main__':
    PORT = 3000
    server = HTTPServer(('0.0.0.0', PORT), SmartWayHandler)
    print(f"🚀 VNA SmartWay HTTP Server with integrated API")
    print(f"   Local: http://localhost:{PORT}")
    print(f"   API: http://localhost:{PORT}/api/notifications")
    print(f"   Files: d:\\Smartway")
    print(f"\n✅ Server running on port {PORT}")
    print(f"   Access web app: http://localhost:{PORT}/VNA%20SmartWay%20V%201.7.html")
    print(f"   Access admin: http://localhost:{PORT}/admin-manage-notifications.html")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
