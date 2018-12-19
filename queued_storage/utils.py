from importlib import import_module
import six
from django.core.exceptions import ImproperlyConfigured
from google.cloud import storage


CLOUD_STORAGE_BUCKET = 'irene-ai'


def import_attribute(import_path=None, options=None):
    if import_path is None:
        raise ImproperlyConfigured("No import path was given.")
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a module." % import_path)
    module, classname = import_path[:dot], import_path[dot + 1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured(
            'Module "%s" does not define a "%s" class.' % (module, classname))


def upload_file_to_gcs(filename):
    """
    Uploads a file to a given Cloud Storage bucket and returns the public url
    to the new object.
    """

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(CLOUD_STORAGE_BUCKET)

    blob = bucket.blob(filename)
    blob.upload_from_filename(filename)

    # url = blob.public_url
    url = "gs://"+CLOUD_STORAGE_BUCKET+"/"+filename

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')
    return url


