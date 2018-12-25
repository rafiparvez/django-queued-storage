from pydub import AudioSegment
raw_path='audio2.raw'
song = AudioSegment.from_raw(raw_path)
flac_path = 'audio2.flac'
song.export(flac_path, format="flac")


audio = requests.get('http://somesite.com/some.mp3')
sox = shutil.which('sox') or glob.glob('C:\Program Files*\sox*\sox.exe')[0]
p = subprocess.Popen(sox + ' -t mp3 - -t flac - rate 16k', stdin = subprocess.PIPE, stdout = subprocess.PIPE, shell = True)
