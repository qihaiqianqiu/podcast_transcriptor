import re
import os
import whisper
import pandas as pd
from pydub import AudioSegment
from tqdm import tqdm
from pyannote.audio import Pipeline
import pyannote.core.annotation as annotation
import time
import torch, torchaudio
from pyannote.audio.pipelines.utils.hook import ProgressHook
from collections import Counter
import json
import gc
from datetime import timedelta

    
def diarization(sample_file_path:str) -> list:
    """
    Parameters
        ----------
        yield_label : bool, optional
            When True, yield (segment, track, label) tuples, such that
            annotation[segment, track] == label. Defaults to yielding
            (segment, track) tuple.
        ----------
        segment : pyannote.core.Segment
        start (float) – interval start time, in seconds.
        end (float) – interval end time, in seconds.

    Args:
        sample_file_path (str): audio file path
    Returns:
        list: [output_path, file_name]
    """
    print(sample_file_path)
    file_name, file_extensions = os.path.splitext(os.path.basename(sample_file_path))
    with open(os.path.join(BASE_DIR, "transcripted.txt"), "r") as infile:
        trancripted = infile.readlines()
    if file_name + "\n" in trancripted:
        print("Transcripted audio, skipping...")
        return
    global pipeline
    start_time = time.time()
    waveform, sample_rate = torchaudio.load(sample_file_path)
    print("audio load time cost: ", time.time() - start_time)
    print("Processing ", sample_file_path)
    annote = annotation.Annotation()
    output_path = os.path.dirname(sample_file_path)
    output_path = os.path.dirname(output_path)
    if not os.path.exists(os.path.join(output_path, "diarizations")):
        os.mkdir(os.path.join(output_path, "diarizations"))
    output_path = os.path.join(output_path, "diarizations", file_name + "_diarization.txt")
    with ProgressHook() as hook:
        dz = pipeline({"waveform": waveform, "sample_rate": sample_rate}, hook=hook)

    c_duration = Counter()
    # Dump the diarization output to disk
    with open(output_path, "w") as text_file:
        for seg, track, speaker in dz.itertracks(yield_label=True):
          time_dur = seg.end - seg.start
          c_duration[speaker] += time_dur

    # Filter background music and very short segments
    sorted_counter = sorted(c_duration.items(), key=lambda x: x[1], reverse=True)
    top_two_keys = [sorted_counter[0][0], sorted_counter[1][0]]

    with open(output_path, "w") as text_file:
        for seg, track, speaker in dz.itertracks(yield_label=True):
          if speaker in top_two_keys:
            annote[seg, track] = speaker
        text_file.write(str(annote))

    text_file.close()
    del waveform, sample_rate, dz, annote, hook, c_duration, sorted_counter, top_two_keys
    torch.cuda.empty_cache()
    gc.collect()
    print("diarization time cost: ", time.time() - start_time)
    return [output_path, file_name]
        
def millisec(timeStr):
    spl = timeStr.split(":")
    s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
    return s

def group_segments(diary_res:list) -> str:
    diary_path = diary_res[0]
    diary = diary_res[1]
    dzs = open(diary_path).read().splitlines()
    res = []
    temp = []
    lastend = 0
    # Put segments with the same speaker together
    for d in dzs:   
        if temp and (temp[0].split()[-1] != d.split()[-1]):      #same speaker
            res.append(temp)
            temp = []
        temp.append(d)
    
        end = re.findall('[0-9]+:[0-9]+:[0-9]+.[0-9]+', string=d)[1]
        end = millisec(end)
        if (lastend > end):       #segment engulfed by a previous segment
            res.append(temp)
            temp = [] 
        else:
            lastend = end
    if temp:
        res.append(temp)
    sound_path = os.path.dirname(diary_path)
    sound_path = os.path.dirname(sound_path)
    seg_path = os.path.join(sound_path, "segmented_audio")
    if not os.path.exists(seg_path):
        os.mkdir(seg_path)
    if not os.path.exists(os.path.join(seg_path, diary)):
        os.mkdir(os.path.join(seg_path, diary))
    sound_path = os.path.join(sound_path, "original_soundtrack", diary + ".mp3")
    audio = AudioSegment.from_mp3(sound_path)
    os.chdir(os.path.join(seg_path, diary))
    gidx = -1
    for g in res:
        start = re.findall('[0-9]+:[0-9]+:[0-9]+.[0-9]+', string=g[0])[0]
        end = re.findall('[0-9]+:[0-9]+:[0-9]+.[0-9]+', string=g[-1])[1]
        start = millisec(start) #- spacermilli
        end = millisec(end)  #- spacermilli
        gidx += 1
        audio[start:end].export(str(gidx) + '.wav', format='wav')
        #print(f"group {gidx}: {start}--{end}")
    return os.path.join(seg_path, diary)

def transcription(segment_path:str) -> None:
    """
    podcast_paths = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    for podcast_path in podcast_paths:
        os.chdir(os.path.join(BASE_DIR, podcast_path))
        podcasts = [f for f in os.listdir() if f.endswith(".mp3")]
        for podcast in podcasts:
            print("Processing ", podcast)
            podcast_path = os.path.join(BASE_DIR, podcast_path, podcast)
            result = model.transcribe(podcast_path, language="en", verbose=True)
            segmented = result["segments"]
            df = pd.DataFrame(segmented)
            df.to_csv(podcast + "_transcription.csv", encoding='utf-8', index=False)
            print("Transcription saved to ", podcast + "_transcription.csv")
    """
    global model, BASE_DIR
    # Skip transcripted audio
    with open(os.path.join(BASE_DIR, "transcripted.txt"), "r") as infile:
        trancripted = infile.readlines()
    if os.path.basename(segment_path) + "\n" in trancripted:
        print("Transcripted audio, skipping...")
        return
    os.chdir(segment_path)
    segments = [f for f in os.listdir(segment_path) if f.endswith(".wav")]
    for audiof in tqdm(segments):
        result = model.transcribe(audio=audiof, language='en', word_timestamps=True)#, initial_prompt=result.get('text', ""))
        file_name, file_extension = os.path.splitext(audiof)
        with open(file_name + '.json', "w") as outfile:
            json.dump(result, outfile, indent=4)  
    with open(os.path.join(BASE_DIR, "transcripted.txt"), "a") as outfile:
        outfile.write(os.path.basename(segment_path) + "\n")
    print("Transcription log saved")
    
def to_html():
    Source = 'Youtube'
    speakers = {'SPEAKER_01':('Interviewer', '#e1ffc7', 'darkgreen'), 'SPEAKER_02':('Customer', 'white', 'darkorange') }
    def_boxclr = 'white'
    def_spkrclr = 'orange'
    if Source == 'Youtube':
        preS = '<!DOCTYPE html>\n<html lang="en">\n\n<head>\n\t<meta charset="UTF-8">\n\t<meta name="viewport" content="width=device-width, initial-scale=1.0">\n\t<meta http-equiv="X-UA-Compatible" content="ie=edge">\n\t<title>' + \
    video_title+ \
    '</title>\n\t<style>\n\t\tbody {\n\t\t\tfont-family: sans-serif;\n\t\t\tfont-size: 14px;\n\t\t\tcolor: #111;\n\t\t\tpadding: 0 0 1em 0;\n\t\t\tbackground-color: #efe7dd;\n\t\t}\n\n\t\ttable {\n\t\t\tborder-spacing: 10px;\n\t\t}\n\n\t\tth {\n\t\t\ttext-align: left;\n\t\t}\n\n\t\t.lt {\n\t\t\tcolor: inherit;\n\t\t\ttext-decoration: inherit;\n\t\t}\n\n\t\t.l {\n\t\t\tcolor: #050;\n\t\t}\n\n\t\t.s {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.c {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.e {\n\t\t\t/*background-color: white; Changing background color */\n\t\t\tborder-radius: 10px;\n\t\t\t/* Making border radius */\n\t\t\twidth: 50%;\n\t\t\t/* Making auto-sizable width */\n\t\t\tpadding: 0 0 0 0;\n\t\t\t/* Making space around letters */\n\t\t\tfont-size: 14px;\n\t\t\t/* Changing font size */\n\t\t\tmargin-bottom: 0;\n\t\t}\n\n\t\t.t {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t#player-div {\n\t\t\tposition: sticky;\n\t\t\ttop: 20px;\n\t\t\tfloat: right;\n\t\t\twidth: 40%\n\t\t}\n\n\t\t#player {\n\t\t\taspect-ratio: 16 / 9;\n\t\t\twidth: 100%;\n\t\t\theight: auto;\n\n\t\t}\n\n\t\ta {\n\t\t\tdisplay: inline;\n\t\t}\n\t</style>\n\t<script>\n\t\tvar tag = document.createElement(\'script\');\n\t\ttag.src = "https://www.youtube.com/iframe_api";\n\t\tvar firstScriptTag = document.getElementsByTagName(\'script\')[0];\n\t\tfirstScriptTag.parentNode.insertBefore(tag, firstScriptTag);\n\t\tvar player;\n\t\tfunction onYouTubeIframeAPIReady() {\n\t\t\tplayer = new YT.Player(\'player\', {\n\t\t\t\t//height: \'210\',\n\t\t\t\t//width: \'340\',\n\t\t\t\tvideoId: \''+ \
    video_id + \
    '\',\n\t\t\t});\n\n\n\n\t\t\t// This is the source "window" that will emit the events.\n\t\t\tvar iframeWindow = player.getIframe().contentWindow;\n\t\t\tvar lastword = null;\n\n\t\t\t// So we can compare against new updates.\n\t\t\tvar lastTimeUpdate = "-1";\n\n\t\t\t// Listen to events triggered by postMessage,\n\t\t\t// this is how different windows in a browser\n\t\t\t// (such as a popup or iFrame) can communicate.\n\t\t\t// See: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage\n\t\t\twindow.addEventListener("message", function (event) {\n\t\t\t\t// Check that the event was sent from the YouTube IFrame.\n\t\t\t\tif (event.source === iframeWindow) {\n\t\t\t\t\tvar data = JSON.parse(event.data);\n\n\t\t\t\t\t// The "infoDelivery" event is used by YT to transmit any\n\t\t\t\t\t// kind of information change in the player,\n\t\t\t\t\t// such as the current time or a playback quality change.\n\t\t\t\t\tif (\n\t\t\t\t\t\tdata.event === "infoDelivery" &&\n\t\t\t\t\t\tdata.info &&\n\t\t\t\t\t\tdata.info.currentTime\n\t\t\t\t\t) {\n\t\t\t\t\t\t// currentTime is emitted very frequently (milliseconds),\n\t\t\t\t\t\t// but we only care about whole second changes.\n\t\t\t\t\t\tvar ts = (data.info.currentTime).toFixed(1).toString();\n\t\t\t\t\t\tts = (Math.round((data.info.currentTime) * 5) / 5).toFixed(1);\n\t\t\t\t\t\tts = ts.toString();\n\t\t\t\t\t\tconsole.log(ts)\n\t\t\t\t\t\tif (ts !== lastTimeUpdate) {\n\t\t\t\t\t\t\tlastTimeUpdate = ts;\n\n\t\t\t\t\t\t\t// It\'s now up to you to format the time.\n\t\t\t\t\t\t\t//document.getElementById("time2").innerHTML = time;\n\t\t\t\t\t\t\tword = document.getElementById(ts)\n\t\t\t\t\t\t\tif (word) {\n\t\t\t\t\t\t\t\tif (lastword) {\n\t\t\t\t\t\t\t\t\tlastword.style.fontWeight = \'normal\';\n\t\t\t\t\t\t\t\t}\n\t\t\t\t\t\t\t\tlastword = word;\n\t\t\t\t\t\t\t\t//word.style.textDecoration = \'underline\';\n\t\t\t\t\t\t\t\tword.style.fontWeight = \'bold\';\n\n\t\t\t\t\t\t\t\tlet toggle = document.getElementById("autoscroll");\n\t\t\t\t\t\t\t\tif (toggle.checked) {\n\t\t\t\t\t\t\t\t\tlet position = word.offsetTop - 20;\n\t\t\t\t\t\t\t\t\twindow.scrollTo({\n\t\t\t\t\t\t\t\t\t\ttop: position,\n\t\t\t\t\t\t\t\t\t\tbehavior: \'smooth\'\n\t\t\t\t\t\t\t\t\t});\n\t\t\t\t\t\t\t\t}\n\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t})\n\t\t}\n\t\tfunction jumptoTime(timepoint, id) {\n\t\t\tevent.preventDefault();\n\t\t\thistory.pushState(null, null, "#" + id);\n\t\t\tplayer.seekTo(timepoint);\n\t\t\tplayer.playVideo();\n\t\t}\n\t</script>\n</head>\n\n<body>\n\t<h2>'  + \
    video_title + \
    '</h2>\n\t<i>Click on a part of the transcription, to jump to its video, and get an anchor to it in the address\n\t\tbar<br><br></i>\n\t<div id="player-div">\n\t\t<div id="player"></div>\n\t\t<div><label for="autoscroll">auto-scroll: </label>\n\t\t\t<input type="checkbox" id="autoscroll" checked>\n\t\t</div>\n\t</div>\n  '
    else:
        preS = '\n<!DOCTYPE html>\n<html lang="en">\n\n<head>\n\t<meta charset="UTF-8">\n\t<meta name="viewport" content="whtmlidth=device-width, initial-scale=1.0">\n\t<meta http-equiv="X-UA-Compatible" content="ie=edge">\n\t<title>' + \
    audio_title+ \
    '</title>\n\t<style>\n\t\tbody {\n\t\t\tfont-family: sans-serif;\n\t\t\tfont-size: 14px;\n\t\t\tcolor: #111;\n\t\t\tpadding: 0 0 1em 0;\n\t\t\tbackground-color: #efe7dd;\n\t\t}\n\n\t\ttable {\n\t\t\tborder-spacing: 10px;\n\t\t}\n\n\t\tth {\n\t\t\ttext-align: left;\n\t\t}\n\n\t\t.lt {\n\t\t\tcolor: inherit;\n\t\t\ttext-decoration: inherit;\n\t\t}\n\n\t\t.l {\n\t\t\tcolor: #050;\n\t\t}\n\n\t\t.s {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.c {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.e {\n\t\t\t/*background-color: white; Changing background color */\n\t\t\tborder-radius: 10px;\n\t\t\t/* Making border radius */\n\t\t\twidth: 50%;\n\t\t\t/* Making auto-sizable width */\n\t\t\tpadding: 0 0 0 0;\n\t\t\t/* Making space around letters */\n\t\t\tfont-size: 14px;\n\t\t\t/* Changing font size */\n\t\t\tmargin-bottom: 0;\n\t\t}\n\n\t\t.t {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t#player-div {\n\t\t\tposition: sticky;\n\t\t\ttop: 20px;\n\t\t\tfloat: right;\n\t\t\twidth: 40%\n\t\t}\n\n\t\t#player {\n\t\t\taspect-ratio: 16 / 9;\n\t\t\twidth: 100%;\n\t\t\theight: auto;\n\t\t}\n\n\t\ta {\n\t\t\tdisplay: inline;\n\t\t}\n\t</style>';
        preS += '\n\t<script>\n\twindow.onload = function () {\n\t\t\tvar player = document.getElementById("audio_player");\n\t\t\tvar player;\n\t\t\tvar lastword = null;\n\n\t\t\t// So we can compare against new updates.\n\t\t\tvar lastTimeUpdate = "-1";\n\n\t\t\tsetInterval(function () {\n\t\t\t\t// currentTime is checked very frequently (1 millisecond),\n\t\t\t\t// but we only care about whole second changes.\n\t\t\t\tvar ts = (player.currentTime).toFixed(1).toString();\n\t\t\t\tts = (Math.round((player.currentTime) * 5) / 5).toFixed(1);\n\t\t\t\tts = ts.toString();\n\t\t\t\tconsole.log(ts);\n\t\t\t\tif (ts !== lastTimeUpdate) {\n\t\t\t\t\tlastTimeUpdate = ts;\n\n\t\t\t\t\t// Its now up to you to format the time.\n\t\t\t\t\tword = document.getElementById(ts)\n\t\t\t\t\tif (word) {\n\t\t\t\t\t\tif (lastword) {\n\t\t\t\t\t\t\tlastword.style.fontWeight = "normal";\n\t\t\t\t\t\t}\n\t\t\t\t\t\tlastword = word;\n\t\t\t\t\t\t//word.style.textDecoration = "underline";\n\t\t\t\t\t\tword.style.fontWeight = "bold";\n\n\t\t\t\t\t\tlet toggle = document.getElementById("autoscroll");\n\t\t\t\t\t\tif (toggle.checked) {\n\t\t\t\t\t\t\tlet position = word.offsetTop - 20;\n\t\t\t\t\t\t\twindow.scrollTo({\n\t\t\t\t\t\t\t\ttop: position,\n\t\t\t\t\t\t\t\tbehavior: "smooth"\n\t\t\t\t\t\t\t});\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}, 0.1);\n\t\t}\n\n\t\tfunction jumptoTime(timepoint, id) {\n\t\t\tvar player = document.getElementById("audio_player");\n\t\t\thistory.pushState(null, null, "#" + id);\n\t\t\tplayer.pause();\n\t\t\tplayer.currentTime = timepoint;\n\t\t\tplayer.play();\n\t\t}\n\t\t</script>\n\t</head>';
        preS += '\n\n<body>\n\t<h2>' + audio_title + '</h2>\n\t<i>Click on a part of the transcription, to jump to its portion of audio, and get an anchor to it in the address\n\t\tbar<br><br></i>\n\t<div id="player-div">\n\t\t<div id="player">\n\t\t\t<audio controls="controls" id="audio_player">\n\t\t\t\t<source src="input.wav" />\n\t\t\t</audio>\n\t\t</div>\n\t\t<div><label for="autoscroll">auto-scroll: </label>\n\t\t\t<input type="checkbox" id="autoscroll" checked>\n\t\t</div>\n\t</div>\n';
    postS = '\t</body>\n</html>'
    
def one_punch(audio_path:str) -> None:
    try:
        res = diarization(audio_path)
        segmented_path = group_segments(res)
        print(segmented_path)
        transcription(segmented_path)   
    except Exception as e:
        print(e)

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Pyannote token
    access_token = "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"
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=access_token)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device: ", device)
    pipeline.to(device)
    # Load the whisper model
    model = whisper.load_model("large", device=device)
    
    dir_lst = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".")]
    soundtracks = [os.path.join(BASE_DIR, d, "original_soundtrack") for d in dir_lst]
    original_audios = [os.path.join(d, f) for d in soundtracks for f in os.listdir(d) if f.endswith(".mp3")]
    for audio in original_audios:
        one_punch(audio)


    
 