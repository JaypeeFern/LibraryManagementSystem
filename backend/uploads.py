import zipfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


MAX_TOPIC_FILE_BYTES = 25 * 1024 * 1024
MAX_STORY_VIDEO_BYTES = 100 * 1024 * 1024
MAX_STORY_THUMBNAIL_BYTES = 5 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = MAX_STORY_VIDEO_BYTES + MAX_STORY_THUMBNAIL_BYTES

UPLOAD_LIMITS_BY_FIELD = {
    'topic_file': MAX_TOPIC_FILE_BYTES,
    'story_vid': MAX_STORY_VIDEO_BYTES,
    'story_thumbnail': MAX_STORY_THUMBNAIL_BYTES,
}


def _validate_size(uploaded_file, maximum_bytes):
    if uploaded_file.size > maximum_bytes:
        raise ValidationError(
            'The file must be no larger than %(limit)s MB.',
            code='file_too_large',
            params={'limit': maximum_bytes // (1024 * 1024)},
        )


def _validate_extension(uploaded_file, allowed_extensions):
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in allowed_extensions:
        allowed = ', '.join(sorted(allowed_extensions))
        raise ValidationError(
            'Choose a file with one of these extensions: %(extensions)s.',
            code='invalid_file_type',
            params={'extensions': allowed},
        )
    return extension


def _read_prefix(uploaded_file, length):
    uploaded_file.open('rb')
    try:
        return uploaded_file.read(length)
    finally:
        uploaded_file.seek(0)


def _is_new_upload(uploaded_file):
    return isinstance(uploaded_file, UploadedFile) or isinstance(
        getattr(uploaded_file, '_file', None),
        UploadedFile,
    )


def _has_zip_member(uploaded_file, member_name):
    uploaded_file.open('rb')
    try:
        with zipfile.ZipFile(uploaded_file) as package:
            return member_name in package.namelist()
    except (OSError, ValueError, zipfile.BadZipFile):
        return False
    finally:
        uploaded_file.seek(0)


def validate_topic_file(uploaded_file):
    if not _is_new_upload(uploaded_file):
        return

    _validate_size(uploaded_file, MAX_TOPIC_FILE_BYTES)
    extension = _validate_extension(uploaded_file, {'.pdf', '.docx', '.pptx'})

    if extension == '.pdf':
        if not _read_prefix(uploaded_file, 5).startswith(b'%PDF-'):
            raise ValidationError('The file content is not a PDF.', code='invalid_file_content')
        return

    required_member = 'word/document.xml' if extension == '.docx' else 'ppt/presentation.xml'
    if not _has_zip_member(uploaded_file, required_member):
        raise ValidationError(
            'The file content does not match the selected Office document type.',
            code='invalid_file_content',
        )


def validate_story_video(uploaded_file):
    if not _is_new_upload(uploaded_file):
        return

    _validate_size(uploaded_file, MAX_STORY_VIDEO_BYTES)
    _validate_extension(uploaded_file, {'.mp4'})
    header = _read_prefix(uploaded_file, 8)
    if len(header) < 8 or header[4:8] != b'ftyp':
        raise ValidationError('The file content is not an MP4 video.', code='invalid_file_content')


def validate_story_thumbnail(uploaded_file):
    if not _is_new_upload(uploaded_file):
        return

    _validate_size(uploaded_file, MAX_STORY_THUMBNAIL_BYTES)
    extension = _validate_extension(uploaded_file, {'.jpg', '.jpeg', '.png'})
    header = _read_prefix(uploaded_file, 8)
    is_jpeg = extension in {'.jpg', '.jpeg'} and header.startswith(b'\xff\xd8\xff')
    is_png = extension == '.png' and header == b'\x89PNG\r\n\x1a\n'
    if not (is_jpeg or is_png):
        raise ValidationError('The file content does not match the selected image type.', code='invalid_file_content')


class UploadLimitHandler(FileUploadHandler):
    """Stop oversized multipart requests before the remaining handlers spool them to disk."""

    def __init__(self, request=None):
        super().__init__(request)
        self.total_bytes_received = 0
        self.current_file_limit = 0

    def new_file(self, field_name, file_name, content_type, content_length, charset, content_type_extra):
        super().new_file(field_name, file_name, content_type, content_length, charset, content_type_extra)
        self.current_file_limit = UPLOAD_LIMITS_BY_FIELD.get(field_name, 0)

    def receive_data_chunk(self, raw_data, start):
        next_file_size = start + len(raw_data)
        next_total_size = self.total_bytes_received + len(raw_data)
        if next_file_size > self.current_file_limit or next_total_size > MAX_TOTAL_UPLOAD_BYTES:
            self.request.upload_limit_exceeded = True
            raise StopUpload(connection_reset=False)

        self.total_bytes_received = next_total_size
        return raw_data

    def file_complete(self, file_size):
        return None


class UploadLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.upload_limit_exceeded = False
        if request.method == 'POST':
            request.upload_handlers.insert(0, UploadLimitHandler(request))

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == 'POST' and request.content_type == 'multipart/form-data':
            request.POST
        if request.upload_limit_exceeded:
            return HttpResponse('Uploaded file exceeds the allowed size limit.', status=413)
        return None
