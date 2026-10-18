import os
import re
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class RangesMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if response.status_code != 200 or not hasattr(response, 'file_to_stream'):
            return response
        http_range = request.META.get('HTTP_RANGE')
        if not (http_range and http_range.startswith('bytes=')):
            return response
        if_range = request.META.get('HTTP_IF_RANGE')
        if if_range and if_range != response.get('Last-Modified') and if_range != response.get('ETag'):
            return response
        f = response.file_to_stream
        statobj = os.fstat(f.fileno())
        range_spec = http_range[len('bytes='):]
        if ',' in range_spec:
            # Multiple ranges are unsupported; serve the complete representation.
            return response
        if not re.fullmatch(r'(?:[0-9]+-[0-9]*|-[0-9]+)', range_spec):
            return self._range_not_satisfiable(response, statobj.st_size)

        first, last = range_spec.split('-', 1)
        if statobj.st_size == 0:
            return self._range_not_satisfiable(response, statobj.st_size)

        try:
            if not first:  # requesting the last N bytes
                suffix_length = int(last)
                if suffix_length == 0:
                    return self._range_not_satisfiable(response, statobj.st_size)
                start = max(0, statobj.st_size - suffix_length)
                end = statobj.st_size - 1
            else:
                start = int(first)
                end = int(last) if last else statobj.st_size - 1
        except ValueError:
            return self._range_not_satisfiable(response, statobj.st_size)

        if start >= statobj.st_size or end < start:
            return self._range_not_satisfiable(response, statobj.st_size)
        end = min(end, statobj.st_size - 1)
        f.seek(start)
        old_read = f.read
        f.read = lambda n: old_read(min(n, end + 1 - f.tell()))
        response.status_code = 206
        response['Content-Length'] = end + 1 - start
        response['Content-Range'] = 'bytes %d-%d/%d' % (start, end, statobj.st_size)
        return response

    @staticmethod
    def _range_not_satisfiable(response, file_size):
        response.close()
        return HttpResponse(
            status=416,
            headers={
                'Accept-Ranges': 'bytes',
                'Content-Range': f'bytes */{file_size}',
            },
        )
