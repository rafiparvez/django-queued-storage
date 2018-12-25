import six
from google.cloud import storage
from google.cloud import speech_v1p1beta1 as speech

CLOUD_STORAGE_BUCKET = 'irene-ai'

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




