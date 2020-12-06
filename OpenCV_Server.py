from http.server import HTTPServer,BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import webbrowser
import cv2
import time
import socket

# Set host port
host_port = 8000
ip_address = '192.168.86.89'#'localhost'
status= 'not connected'
my_IP = socket.gethostbyname(socket.gethostname())
URL='%s:%d'%(ip_address,host_port)

# Webserver
class MyServer(BaseHTTPRequestHandler):

    def standardPage(self,goal = 'start'):
        if goal == 'start':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(('''<html><head><title>Rogers Camera Code</title></head>
                        <body><p>Rogers Camera  (%s)<br>Camera Status: %s</p>
                        <a href = "http://%s/settings">Current Settings</a><br>
                        <a href = "http://%s/init">Initialize Camera</a><br>
                        <a href = "http://%s/snap">Snap an Image</a><br>
                        <a href = "http://%s/grab">Stream Images</a><br>
                        <a href = "http://%s/close">Close Camera Connection</a><br><br><br>
                        <form action="/settings"> 
                        <label for="camera">Camera:</label>  
                        <input type="number" id="camera" name="camera" value="%d"><br> 
                        <label for="scale">Scale Percent:</label>  
                        <input type="number" id="scale" name="scale" value="%d"><br>  
                        <label for="rotate">Orientation:</label> 
                        <select name="rotate" id="rotate" value="%d"> 
                          <option value="-1">no rotation</option> 
                          <option value="0">90 CW</option> 
                          <option value="1">180</option> 
                          <option value="2">90 CCW</option> 
                        </select> <br><br>
                        <input type="submit" value="Update">  
                    </form>'''%(my_IP,status,URL,URL,URL,URL,URL,camera,scale_percent,rotate)).encode("utf-8"))
            self.wfile.write(("<hr><p>Executing command: %s</p>" % self.path).encode("utf-8"))
        else:
            self.wfile.write("</body></html>\r\n".encode("utf-8"))

    def getSettings(self,Format = 'text'):
        reply = 'Settings:\nCamera = %d\nscaling = %d\nRotation = %d'%(camera,scale_percent,rotate)
        if (Format == 'HTML'):
            reply = reply.replace('\n','<br>')
        return reply

    def parameters(self,url):
        global camera,scale_percent,rotate
        if len(url) <= 1:
            return False  # there were no parameters defined
        path = url[0]
        cmds = url[1].split(b'&')
        if (path == b'/settings'):
            for cmd in cmds:
                params = cmd.split(b'=')
                value = float(params[1])
                param = params[0]
                if (param == b'camera'):
                    camera = int(value)
                if (param == b'rotation'):
                    rotate = int(value)
                if (param == b'scale'):
                    scale_percent = int(value)
            print(self.getSettings())
            self.standardPage()
            self.wfile.write(self.getSettings('HTML').encode("utf-8"))
            self.standardPage('end')
        return True
        
    def do_GET(self):
        global camera,cap,scale_percent,rotate,status
        url = self.path.encode("utf-8").split(b'?')
        print(url)
        if self.parameters(url):
            return
        if (url[0] == b'/'):
            self.standardPage()
        elif (url[0] == b'/settings'):
            self.standardPage()
            self.wfile.write(self.getSettings('HTML').encode("utf-8"))
        elif (url[0] == b'/init'):
            cap = cv2.VideoCapture(camera)
            status = 'connected'
            self.standardPage()
            self.wfile.write('initializing camera # {}'.format(str(camera)).encode("utf-8"))
            print('setting up camera %d'% (camera))
        elif (url[0] == b'/snap'):
            self.standardPage()
            self.wfile.write('snapping from camera # {}'.format(str(camera)).encode("utf-8"))
            self.wfile.write(('<br><br><img src="http://%s/snap.jpg">'%(URL)).encode("utf-8"))
        elif (url[0] == b'/snap.jpg'):
            success, image = self.Snap()
            if success:
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Content-length',str(image.size))
                self.end_headers()
                self.wfile.write(bytearray(image))
                return
            else:
                self.standardPage()
                self.wfile.write('cannot grab image'.encode())
        elif (url[0] == b'/grab'):
            self.standardPage()
            self.wfile.write('grabbing from camera # {}'.format(str(camera)).encode("utf-8"))
            self.wfile.write(('<br><br><iframe src="http://%s/grab.mjpg"></iframe>'%(URL)).encode("utf-8"))
        elif (url[0] == b'/grab.mjpg'):
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            fails = 0
            while True:
                try:
                    success, image = self.Snap()
                    #cv2.imshow('frame',image) seems to crash things
                    if success:
                        fails = 0
                        self.wfile.write('--jpgboundary\r\n'.encode())
                        self.send_header('Content-type','image/jpeg')
                        self.send_header('Content-length',str(image.size))
                        self.end_headers()
                        self.wfile.write(bytearray(image))
                    else:
                        fails += 1
                        if fails > 10:
                            break
                    time.sleep(0.05)
                except KeyboardInterrupt:
                    print(e)
                    break
            return
        elif (url[0] == b'/close'):
            status = 'not connected'
            self.standardPage()
            self.wfile.write('closing camera # {}'.format(str(camera)).encode("utf-8"))
            cap.release()
            cv2.destroyAllWindows()
        else:
            self.standardPage()
            self.wfile.write('unsupported path'.encode("utf-8"))
        self.standardPage('end')

    def Snap(self):
        global cap,scale_percent, rotate
        if not cap:
            print('camera not initialized')
            return False, None
        ret, frame = cap.read()
        if not ret:
            print('cannot grab image')
            return False, None
        frame = cv2.cvtColor(frame,cv2.COLOR_BGRA2BGR)
        if (rotate >= 0) : frame = cv2.rotate(frame, rotate)
        width = int(frame.shape[1] * scale_percent / 100)
        height = int(frame.shape[0] * scale_percent / 100)
        dim = (width, height)  
        frame = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag:
            print('encoding error')
            return False, None
        return True, encodedImage

            
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests in a separate thread."""
            
        # Create Webserver
if __name__ == '__main__':
    global camera,cap,scale_percent,rotate
    cap = None
    camera = 0
    scale_percent = 50  # percent of original size
    rotate = cv2.cv2.ROTATE_90_CLOCKWISE
    
    http_server = ThreadedHTTPServer((ip_address, host_port), MyServer)
    print("Server Starts - %s:%s" % (ip_address, host_port))
    #webbrowser.open_new('http://%s:%s' %  (ip_address, host_port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
        print("\n-------------------EXIT-------------------")

