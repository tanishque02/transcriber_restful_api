from flask import Flask
from flask_restful import Api, Resource, abort, reqparse
import wave
from pytube import YouTube
from pyAudioAnalysis import audioBasicIO as aIO
from pyAudioAnalysis import audioSegmentation as AS
import os
import subprocess
import datetime
import numpy as np
from deepspeech import Model
import scipy

def yurl(url):
    new_url = "https://www.youtube.com/watch?v="+url
    return new_url

def audio_video(url):
  video = YouTube(url).streams.filter(progressive = True, res = '360p')
  video_path = video.first().download()
  os.rename(video_path, video_path.replace(' ', '-'))
  new_video_path = video_path.replace(' ', '-')
  audio_path = new_video_path.replace(".mp4", "-audio.wav")
  extractAudio(new_video_path, audio_path)
  return audio_path


def silenceRemoval(input_file, smoothing_window = 1.0, weight = 0.2):
    [fs, x] = aIO.read_audio_file(input_file)
    segmentLimits = AS.silence_removal(x, fs, 0.05, 0.05, smoothing_window, weight)
    segment_files = []
    
    for i, s in enumerate(segmentLimits):
        strOut = "{0:s}_{1:.3f}-{2:.3f}.wav".format(input_file[0:-4], s[0], s[1])
        scipy.io.wavfile.write(strOut, fs, x[int(fs * s[0]):int(fs * s[1])])
        segment_files.append(strOut)
      
    return segment_files


def extractAudio(input_file, audio_file_name):
    command = "ffmpeg -hide_banner -loglevel warning -i {} -b:a 192k -ac 1 -ar 16000 -vn {}".format(input_file, audio_file_name)
    try:
        ret = subprocess.call(command, shell=True)
        print("Extracted audio to audio/{}".format(audio_file_name.split("/")[-1]))
    except Exception as e:
        print("Error: ", str(e))
        exit(1)
        

def write_to_file(file_handle, inferred_text, line_count, limits):
    """Write the inferred text to SRT file
    Follows a specific format for SRT files
    Args:
        file_handle : SRT file handle
        inferred_text : text to be written
        line_count : subtitle line count 
        limits : starting and ending times for text
    """
    
    d = str(datetime.timedelta(seconds=float(limits[0])))
    try:
        from_dur = "0" + str(d.split(".")[0]) + "," + str(d.split(".")[-1][:2])
    except:
        from_dur = "0" + str(d) + "," + "00"
        
    d = str(datetime.timedelta(seconds=float(limits[1])))
    try:
        to_dur = "0" + str(d.split(".")[0]) + "," + str(d.split(".")[-1][:2])
    except:
        to_dur = "0" + str(d) + "," + "00"
        
    with open(file_handle, 'a') as f:
      f.write(str(line_count) + "\n")
      f.write(from_dur + " --> " + to_dur + "\n")
      f.write(inferred_text + "\n\n")


def ds_process_audio(audio_file): 
    ds = Model("C:/Users/tanis/deepspeech-0.9.3-models.pbmm")
    ds.enableExternalScorer("C:/Users/tanis/deepspeech-0.9.3-models.scorer")
    
    fin = wave.open(audio_file, 'rb')
    audio = np.frombuffer(fin.readframes(fin.getnframes()), np.int16)
    fin.close()
    
    # Perform inference on audio segment
    infered_text = ds.stt(audio)
    
    # File name contains start and end times in seconds. Extract that
    limits = audio_file.split("/")[-1][:-4].split("_")[-1].split("-")

    return infered_text, limits


def transcribe(url):
  audio_path = audio_video(url)
  segment_files = silenceRemoval(audio_path)

  line_count = 1
  for i in segment_files:
    infered_text, limits = ds_process_audio(i)
    if len(infered_text) !=0:
      write_to_file("srt.srt", infered_text, line_count, limits)
      line_count += 1


class Transcribe(Resource):
    def get(self, url):
        new_url = yurl(url)
        transcribe(new_url)
        with open('srt.srt') as f:
            lines = f.readlines()
        return {"data": lines}

app = Flask(__name__)
api = Api(app)

api.add_resource(Transcribe, "/<string:url>")

if __name__ == "__main__":
    app.run(debug = True)

    
    

# https://www.youtube.com/watch?v=mybSav4MK90