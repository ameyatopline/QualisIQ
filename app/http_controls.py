"""Single-worker defenses; deployment gateway must enforce distributed limits."""
import asyncio,time,uuid
from collections import OrderedDict,deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class HTTPControls(BaseHTTPMiddleware):
    def __init__(self,app):
        super().__init__(app)
    async def dispatch(self,request,call_next):
        request_id=str(uuid.uuid4());blocked=False
        if request.url.path=='/api/v1/auth/login' and request.method=='POST':
            attempts=request.app.state.login_attempts;lock=request.app.state.login_lock
            key=request.client.host if request.client else 'unknown';now=time.monotonic()
            async with lock:
                while attempts and next(iter(attempts.values()))[-1]<now-60:attempts.popitem(last=False)
                bucket=attempts.setdefault(key,deque())
                while bucket and bucket[0]<now-60:bucket.popleft()
                blocked=len(bucket)>=20;bucket.append(now);attempts.move_to_end(key)
                if len(bucket)>21:bucket.popleft()
                if len(attempts)>10000:attempts.popitem(last=False)
        response=JSONResponse({'detail':'Too many login attempts. Try again in one minute.'},429,headers={'Retry-After':'60'}) if blocked else await call_next(request)
        response.headers.update({'X-Request-ID':request_id,'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'DENY','Permissions-Policy':'camera=(), microphone=(), geolocation=()'})
        if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        elif request.url.path not in ('/docs','/redoc'):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response
