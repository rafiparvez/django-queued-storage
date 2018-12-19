from pydub import AudioSegment
raw_path='audio2.raw'
song = AudioSegment.from_raw(raw_path)
flac_path = 'audio2.flac'
song.export(flac_path, format="flac")
