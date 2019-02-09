import io
import re
import six

from django.core.exceptions import ImproperlyConfigured
from fuzzywuzzy import fuzz
from google.cloud import speech, storage
from importlib import import_module

from string import punctuation


CLOUD_STORAGE_BUCKET = 'irene-ai'
SAMPLE_RATE = "16000"


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

#
# def convert_webm(webm_file_path):
#     flac_file_path = webm_file_path # As of now just replace the file
#     sound = AudioSegment.from_file(webm_file_path, codec="opus")
#     sound = sound.set_frame_rate(16000)
#     sound = sound.set_channels(1)
#     sound.export(flac_file_path, format="flac")

def clean_text(text):
    text = re.sub('\s*,\s*', ', ', text)
    text = re.sub('\s*\.\s*', '. ', text)
    text = re.sub('\s*\?\s*', '? ', text)
    text = re.sub('\s*!\s*', '! ', text)
    return text


def get_nearest_substring(tokenized_raw_text, punct_left_substr, punct_right_substr, approx_idx, punct):
    min_dist = 0
    best_idx = -1

    len_raw_text = len(tokenized_raw_text)
    len_neighbour_punct_words = len(punct_left_substr) + len(punct_right_substr)

    # entire search window in the raw text
    begin__srch_window_idx = 0 if approx_idx - 9 < 0 else approx_idx - 9
    end__srch_window_idx = min(approx_idx + 9, len_raw_text - len_neighbour_punct_words)

    punct_left_substr = " ".join(punct_left_substr)
    punct_right_substr = " ".join(punct_right_substr)

    for start_idx in range(begin__srch_window_idx, end__srch_window_idx+1):
        end_srch = start_idx + len_neighbour_punct_words

        for i in range(start_idx, end_srch):
            left_raw_substr = " ".join(tokenized_raw_text[start_idx:i+1])
            right_raw_substr = " ".join(tokenized_raw_text[i+1:end_srch])


            word_dist = fuzz.ratio(left_raw_substr, punct_left_substr) + \
                        fuzz.ratio(right_raw_substr, punct_right_substr)
            if word_dist > min_dist:
                min_dist = word_dist
                best_idx = i+1

    tokenized_raw_text.insert(best_idx, punct)
    return tokenized_raw_text

