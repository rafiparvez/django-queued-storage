import io
import re
import six

from django.core.exceptions import ImproperlyConfigured
from fuzzywuzzy import fuzz
from google.cloud import speech, storage
from importlib import import_module
from pydub import AudioSegment
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


def convert_webm(webm_file_path):
    flac_file_path = webm_file_path # As of now just replace the file
    sound = AudioSegment.from_file(webm_file_path, codec="opus")
    sound = sound.set_frame_rate(16000)
    sound = sound.set_channels(1)
    sound.export(flac_file_path, format="flac")


def transcribe_long_file_with_auto_punctuation(audio_file, lang_code='en-US'):
    """Transcribe the given audio file with auto punctuation enabled."""
    # [START speech_transcribe_auto_punctuation_beta]

    client = speech.SpeechClient()

    print("Begin transcribing {0}".format(audio_file))

    gcs_uri = upload_file_to_gcs(audio_file)
    print("Uploaded file at {0}".format(gcs_uri))

    audio = speech.types.RecognitionAudio(uri=gcs_uri)

    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code=lang_code,
        enable_automatic_punctuation=True,
        # enable_word_confidence=True,
        interim_results=False,
        speech_contexts=[speech.types.SpeechContext(
            phrases=['mote', 'aggregate', 'doctrine'],
        )])

    operation = client.long_running_recognize(config, audio)
    print('Waiting for operation to complete...')
    response = operation.result(timeout=90)

    final_text = ""
    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print('-' * 20)
        print('First alternative of result {}'.format(i))
        print('Transcript: {}'.format(alternative.transcript))
        final_text += alternative.transcript
    return final_text


def transcribe_small_file_with_auto_punctuation(path, lang_code='en_US'):
    """Transcribe the given audio file with auto punctuation enabled."""
    # [START speech_transcribe_auto_punctuation]
    client = speech.SpeechClient()

    # path = 'resources/commercial_mono.wav'
    with io.open(path, 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.types.RecognitionAudio(content=content)
    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code=lang_code,
        # Enable automatic punctuation
        enable_automatic_punctuation=True,
        max_alternatives=1)

    response = client.recognize(config, audio)

    final_text = ""

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print('-' * 20)
        print('First alternative of result {}'.format(i))
        print('Transcript: {}'.format(alternative.transcript))
        final_text += alternative.transcript
    return final_text


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


def punctuate_text(raw_text, punct_text):
    """
    method to move punctuations from one text to another based on fuzzy string
    matchine
    :param raw_text: text without punctuations
    :param punct_text: text with punctuations
    :return: punctuations fit into raw_text
    """
    response=""

    tokenized_raw_text = raw_text.split()
    len_raw_text = len(tokenized_raw_text)

    # tokenized_punct_text = re.findall(r"[\w']+|[.,!?;']", punct_text)
    tokenized_punct_text = re.findall(r"[\w']+|[" + punctuation + "]", punct_text)
    for idx, token in enumerate(tokenized_punct_text):
        if token in punctuation:
            begin_idx = 0 if idx-3 < 0 else idx-3
            end_idx = min(len_raw_text, idx+3)

            punct_left_substr = tokenized_punct_text[begin_idx:idx+1]
            punct_right_substr = tokenized_punct_text[idx+1:end_idx]

            tokenized_raw_text = get_nearest_substring(
                tokenized_raw_text, punct_left_substr, punct_right_substr, idx, token)
    return clean_text(" ".join(tokenized_raw_text))
