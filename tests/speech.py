import six
from google.cloud import storage

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

    url = blob.self_link

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')
    return url

def transcribe_file_with_auto_punctuation(audioFile):
    """Transcribe the given audio file with auto punctuation enabled."""
    # [START speech_transcribe_auto_punctuation_beta]
    # from google.cloud import speech_v1p1beta1 as speech
    from google.cloud import speech
    from google.cloud.speech import enums
    from google.cloud.speech import types

    client = speech.SpeechClient()

    print("Begin transcribing {0}".format(audioFile))

    #  speech_file = 'resources/commercial_mono.wav'
    # speech_file = audioFile
    # with io.open(speech_file, 'rb') as audio_file:
    #     content = audio_file.read()

    gcs_uri = upload_file_to_gcs(audioFile)

    gcs_uri = "gs://irene-ai/audio3.flac"
    print("Uploaded file at {0}".format(gcs_uri))

    # audio = speech.types.RecognitionAudio(content=content)
    audio = types.RecognitionAudio(uri=gcs_uri)
    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code='en-US',
        # Enable automatic punctuation
        enable_automatic_punctuation=True)

    # response = client.recognize(config, audio)
    operation = client.long_running_recognize(config, audio)
    print('Waiting for operation to complete...')
    response = operation.result(timeout=90)

    text_results = ""

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print('-' * 20)
        print('First alternative of result {}'.format(i))
        print('Transcript: {}'.format(alternative.transcript))
        text_results += alternative.transcript + '\n'
    return text_results

# [START speech_transcribe_async_gcs]
def transcribe_gcs(gcs_uri):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""
    from google.cloud import speech
    from google.cloud.speech import enums
    from google.cloud.speech import types
    client = speech.SpeechClient()

    audio = types.RecognitionAudio(uri=gcs_uri)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code='en-US')

    operation = client.long_running_recognize(config, audio)

    print('Waiting for operation to complete...')
    response = operation.result(timeout=90)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        print(u'Transcript: {}'.format(result.alternatives[0].transcript))
        print('Confidence: {}'.format(result.alternatives[0].confidence))
# [END speech_transcribe_async_gcs]


if __name__ == "__main__":
    # transcribe_gcs('audio2.flac')
    transcribe_file_with_auto_punctuation('audio3.flac')

