"""Shared upload validation — restricts uploaded files by extension and size."""
import os

from django.core.exceptions import ValidationError

ALLOWED_UPLOAD_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
    '.png', '.jpg', '.jpeg', '.gif', '.txt',
}
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def validate_upload(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            'Unsupported file type "%(ext)s". Allowed types: %(allowed)s.',
            params={'ext': ext, 'allowed': ', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))},
        )
    if file.size and file.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError('File is too large (maximum 20 MB).')
