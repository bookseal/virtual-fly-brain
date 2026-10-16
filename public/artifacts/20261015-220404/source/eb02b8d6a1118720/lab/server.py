"""Local static preview with byte ranges for synchronized MP4 seeking."""
import argparse,http.server,os,re
from pathlib import Path
from functools import partial
from .store import ROOT

class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path=self.translate_path(self.path);self.remaining=None
        if not os.path.isfile(path):return super().send_head()
        try:stream=open(path,'rb')
        except OSError:self.send_error(404);return None
        stat=os.fstat(stream.fileno());size=stat.st_size;start=0;end=size-1;header=self.headers.get('Range')
        if header:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
            try:
                if not match or not any(match.groups()):raise ValueError()
                left,right=match.groups()
                if left:start=int(left);end=min(int(right),end) if right else end
                else:start=max(0,size-int(right))
                if start>end or start>=size:raise ValueError()
            except ValueError:
                stream.close();self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
        self.send_response(206 if header else 200)
        self.send_header('Content-type',self.guess_type(path));self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Length',str(end-start+1));self.send_header('Last-Modified',self.date_time_string(stat.st_mtime))
        if header:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers();stream.seek(start);self.remaining=end-start+1;return stream
    def copyfile(self,source,outputfile):
        if self.remaining is None:return super().copyfile(source,outputfile)
        try:
            while self.remaining>0:
                chunk=source.read(min(65536,self.remaining))
                if not chunk:break
                outputfile.write(chunk);self.remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);ap.add_argument('--directory',type=Path,default=ROOT/'site');a=ap.parse_args()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),partial(RangeHandler,directory=str(a.directory)));server.serve_forever()
if __name__=='__main__':main()
