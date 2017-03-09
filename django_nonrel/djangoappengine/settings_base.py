try:
    from dev_appserver_version import DEV_APPSERVER_VERSION
except ImportError:
    DEV_APPSERVER_VERSION = 2

# Initialize App Engine SDK if necessary.
try:
    from google.appengine.api import apiproxy_stub_map
except ImportError:
    from djangoappengine.boot import setup_env
    setup_env(DEV_APPSERVER_VERSION)

from djangoappengine.utils import on_production_server, have_appserver


DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'djangoappengine.db',

        # Other settings which you might want to override in your
        # settings.py.

        # Activates high-replication support for remote_api.
        # 'HIGH_REPLICATION': True,

        # Switch to the App Engine for Business domain.
        # 'DOMAIN': 'googleplex.com',

        # Store db.Keys as values of ForeignKey or other related
        # fields. Warning: dump your data before, and reload it after
        # changing! Defaults to False if not set.
        # 'STORE_RELATIONS_AS_DB_KEYS': True,

        'DEV_APPSERVER_OPTIONS': {
            'use_sqlite': True,

            # Optional parameters for development environment.

            # Emulate the high-replication datastore locally.
            # TODO: Likely to break loaddata (some records missing).
            # 'high_replication' : True,

            # Setting to True will trigger exceptions if a needed index is missing
            # Setting to False will auto-generated index.yaml file
            # 'require_indexes': True,
        },
    },
}

if on_production_server:
    EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
else:
    EMAIL_BACKEND = 'djangoappengine.mail.EmailBackend'

# Specify a queue name for the async. email backend.
EMAIL_QUEUE_NAME = 'default'

PREPARE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 0,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

if not on_production_server:
    INTERNAL_IPS = ('127.0.0.1',)
