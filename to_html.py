import re
from openai import OpenAI
import os
import json
from tqdm import tqdm

deepseek_api = "sk-e8224e2c0d194e91a2830bb8893cf3c3"
client = OpenAI(api_key=deepseek_api, base_url="https://api.deepseek.com")
def_boxclr = 'white'
def_spkrclr = 'orange'
            
def millisec(timeStr):
  spl = timeStr.split(":")
  s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
  return s

def timeStr(t):
  return '{0:02d}:{1:02d}:{2:06.2f}'.format(round(t // 3600), 
                                                round(t % 3600 // 60), 
                                                t % 60)
  
def wrap(video_title:str, video_id:str) -> str:
    speakers = {'SPEAKER_01':('Interviewer', '#e1ffc7', 'darkgreen'), 'SPEAKER_02':('Customer', 'white', 'darkorange') }
    def_boxclr = 'white'
    def_spkrclr = 'orange'
    preS = '<!DOCTYPE html>\n<html lang="en">\n\n<head>\n\t<meta charset="UTF-8">\n\t<meta name="viewport" content="width=device-width, initial-scale=1.0">\n\t<meta http-equiv="X-UA-Compatible" content="ie=edge">\n\t<title>' + \
    video_title+ \
    '</title>\n\t<style>\n\t\tbody {\n\t\t\tfont-family: sans-serif;\n\t\t\tfont-size: 14px;\n\t\t\tcolor: #111;\n\t\t\tpadding: 0 0 1em 0;\n\t\t\tbackground-color: #efe7dd;\n\t\t}\n\n\t\ttable {\n\t\t\tborder-spacing: 10px;\n\t\t}\n\n\t\tth {\n\t\t\ttext-align: left;\n\t\t}\n\n\t\t.lt {\n\t\t\tcolor: inherit;\n\t\t\ttext-decoration: inherit;\n\t\t}\n\n\t\t.l {\n\t\t\tcolor: #050;\n\t\t}\n\n\t\t.s {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.c {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t.e {\n\t\t\t/*background-color: white; Changing background color */\n\t\t\tborder-radius: 10px;\n\t\t\t/* Making border radius */\n\t\t\twidth: 50%;\n\t\t\t/* Making auto-sizable width */\n\t\t\tpadding: 0 0 0 0;\n\t\t\t/* Making space around letters */\n\t\t\tfont-size: 14px;\n\t\t\t/* Changing font size */\n\t\t\tmargin-bottom: 0;\n\t\t}\n\n\t\t.t {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t#player-div {\n\t\t\tposition: sticky;\n\t\t\ttop: 20px;\n\t\t\tfloat: right;\n\t\t\twidth: 40%\n\t\t}\n\n\t\t#player {\n\t\t\taspect-ratio: 16 / 9;\n\t\t\twidth: 100%;\n\t\t\theight: auto;\n\n\t\t}\n\n\t\ta {\n\t\t\tdisplay: inline;\n\t\t}\n\t</style>\n\t<script>\n\t\tvar tag = document.createElement(\'script\');\n\t\ttag.src = "https://www.youtube.com/iframe_api";\n\t\tvar firstScriptTag = document.getElementsByTagName(\'script\')[0];\n\t\tfirstScriptTag.parentNode.insertBefore(tag, firstScriptTag);\n\t\tvar player;\n\t\tfunction onYouTubeIframeAPIReady() {\n\t\t\tplayer = new YT.Player(\'player\', {\n\t\t\t\t//height: \'210\',\n\t\t\t\t//width: \'340\',\n\t\t\t\tvideoId: \''+ \
    video_id + \
    '\',\n\t\t\t});\n\n\n\n\t\t\t// This is the source "window" that will emit the events.\n\t\t\tvar iframeWindow = player.getIframe().contentWindow;\n\t\t\tvar lastword = null;\n\n\t\t\t// So we can compare against new updates.\n\t\t\tvar lastTimeUpdate = "-1";\n\n\t\t\t// Listen to events triggered by postMessage,\n\t\t\t// this is how different windows in a browser\n\t\t\t// (such as a popup or iFrame) can communicate.\n\t\t\t// See: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage\n\t\t\twindow.addEventListener("message", function (event) {\n\t\t\t\t// Check that the event was sent from the YouTube IFrame.\n\t\t\t\tif (event.source === iframeWindow) {\n\t\t\t\t\tvar data = JSON.parse(event.data);\n\n\t\t\t\t\t// The "infoDelivery" event is used by YT to transmit any\n\t\t\t\t\t// kind of information change in the player,\n\t\t\t\t\t// such as the current time or a playback quality change.\n\t\t\t\t\tif (\n\t\t\t\t\t\tdata.event === "infoDelivery" &&\n\t\t\t\t\t\tdata.info &&\n\t\t\t\t\t\tdata.info.currentTime\n\t\t\t\t\t) {\n\t\t\t\t\t\t// currentTime is emitted very frequently (milliseconds),\n\t\t\t\t\t\t// but we only care about whole second changes.\n\t\t\t\t\t\tvar ts = (data.info.currentTime).toFixed(1).toString();\n\t\t\t\t\t\tts = (Math.round((data.info.currentTime) * 5) / 5).toFixed(1);\n\t\t\t\t\t\tts = ts.toString();\n\t\t\t\t\t\tconsole.log(ts)\n\t\t\t\t\t\tif (ts !== lastTimeUpdate) {\n\t\t\t\t\t\t\tlastTimeUpdate = ts;\n\n\t\t\t\t\t\t\t// It\'s now up to you to format the time.\n\t\t\t\t\t\t\t//document.getElementById("time2").innerHTML = time;\n\t\t\t\t\t\t\tword = document.getElementById(ts)\n\t\t\t\t\t\t\tif (word) {\n\t\t\t\t\t\t\t\tif (lastword) {\n\t\t\t\t\t\t\t\t\tlastword.style.fontWeight = \'normal\';\n\t\t\t\t\t\t\t\t}\n\t\t\t\t\t\t\t\tlastword = word;\n\t\t\t\t\t\t\t\t//word.style.textDecoration = \'underline\';\n\t\t\t\t\t\t\t\tword.style.fontWeight = \'bold\';\n\n\t\t\t\t\t\t\t\tlet toggle = document.getElementById("autoscroll");\n\t\t\t\t\t\t\t\tif (toggle.checked) {\n\t\t\t\t\t\t\t\t\tlet position = word.offsetTop - 20;\n\t\t\t\t\t\t\t\t\twindow.scrollTo({\n\t\t\t\t\t\t\t\t\t\ttop: position,\n\t\t\t\t\t\t\t\t\t\tbehavior: \'smooth\'\n\t\t\t\t\t\t\t\t\t});\n\t\t\t\t\t\t\t\t}\n\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t})\n\t\t}\n\t\tfunction jumptoTime(timepoint, id) {\n\t\t\tevent.preventDefault();\n\t\t\thistory.pushState(null, null, "#" + id);\n\t\t\tplayer.seekTo(timepoint);\n\t\t\tplayer.playVideo();\n\t\t}\n\t</script>\n</head>\n\n<body>\n\t<h2>'  + \
    video_title + \
    '</h2>\n\t<i>Click on a part of the transcription, to jump to its video, and get an anchor to it in the address\n\t\tbar<br><br></i>\n\t<div id="player-div">\n\t\t<div id="player"></div>\n\t\t<div><label for="autoscroll">auto-scroll: </label>\n\t\t\t<input type="checkbox" id="autoscroll" checked>\n\t\t</div>\n\t</div>\n  '
    postS = '\t</body>\n</html>'
    return preS, postS


def deepseek_trans(text:str) -> str:
    global client
    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
        {"role": "system", "content": "你是一个量化金融领域的中英文翻译专家。将用户输入的英文翻译成中文，提供中文翻译结果。用户可以向助手发送需要翻译的内容，内容均来自于播客，以对话形式展开，助手会回答相应的翻译结果，并确保符合量化金融领域的专业术语，中文语言习惯，你可以调整语气和风格，同时作为翻译家，需将原文翻译成具有准确，优美的播客译文"},
        {"role": "user", "content": text},
        ],
        stream=False
    )
    return completion.choices[0].message.content
        
    
def parse_dira(dirazation_file:str) -> None:
    print("processing " + dirazation_file)
    dzs = open(dirazation_file).read().splitlines()
    video_name = os.path.splitext(os.path.basename(dirazation_file))[0]
    video_title = video_name.split('[')[0]
    video_id = video_name.split('[')[1].split(']')[0]
    preS, postS = wrap(video_title, video_id)
    print("finish baseline html")
    diaraztion_path = os.path.dirname(dirazation_file)
    seasonal_path = os.path.dirname(diaraztion_path)
    segmented_path = os.path.join(seasonal_path, "segmented_audio", f'{video_title}[{video_id}]')
    
    groups = []
    g = []
    lastend = 0
    interviewer = dzs[0].split()[-1]
    for d in dzs:
        if d.split()[-1] != interviewer:
            customer = d.split()[-1]
            break
    speakers = {interviewer:('Interviewer', '#e1ffc7', 'darkgreen'), customer:('Customer', 'white', 'darkorange') }
    for d in dzs:   
        if g and (g[0].split()[-1] != d.split()[-1]):      #same speaker
            groups.append(g)
            g = []
    
        g.append(d)
    
        end = re.findall('[0-9]+:[0-9]+:[0-9]+.[0-9]+', string=d)[1]
        end = millisec(end)
        if (lastend > end):       #segment engulfed by a previous segment
            groups.append(g)
            g = [] 
        else:
            lastend = end
    if g:
        groups.append(g)
    html = list(preS)
    txt = list("")
    gidx = -1
    for g in tqdm(groups, dynamic_ncols=True):  
        shift = re.findall('[0-9]+:[0-9]+:[0-9]+.[0-9]+', string=g[0])[0]
        shift = millisec(shift)  #the start time in the original video
        shift=max(shift, 0)
        gidx += 1
        captions = json.load(open(os.path.join(segmented_path, str(gidx) + '.json')))['segments']
        text = json.load(open(os.path.join(segmented_path, str(gidx) + '.json')))['text']
        if captions:
            translated = deepseek_trans(text)
            speaker = g[0].split()[-1]
            boxclr = def_boxclr
            spkrclr = def_spkrclr
            if speaker in speakers:
                speaker, boxclr, spkrclr = speakers[speaker] 
            
            html.append(f'<div class="e" style="background-color: {boxclr}">\n');
            html.append('<p  style="margin:0;padding: 5px 10px 10px 10px;word-wrap:normal;white-space:normal;">\n')
            html.append(f'<span style="color:{spkrclr};font-weight: bold;">{speaker}</span><br>\n\t\t\t\t')
            
            for c in captions:
                start = shift + c['start'] * 1000.0 
                start = start / 1000.0   #time resolution ot youtube is Second.            
                end = (shift + c['end'] * 1000.0) / 1000.0      
                txt.append(f'[{timeStr(start)} --> {timeStr(end)}] [{speaker}] {c["text"]}\n')

                for i, w in enumerate(c['words']):
                    if w == "":
                        continue
                    start = (shift + w['start']*1000.0) / 1000.0        
                    #end = (shift + w['end']) / 1000.0   #time resolution ot youtube is Second.  
                    html.append(f'<a href="#{timeStr(start)}" id="{"{:.1f}".format(round(start*5)/5)}" class="lt" onclick="jumptoTime({int(start)}, this.id)">{w["word"]}</a><!--\n\t\t\t\t-->')
            #html.append('\n')  
            html.append(f'<p style="margin:0;padding: 5px 10px 10px 10px;word-wrap:normal;white-space:normal;">{translated}</p>')
            html.append('</p>\n')
            html.append(f'</div>\n')
    print("finish html")
    html.append(postS)
    res_path = os.path.join(seasonal_path, "translated_html")
    if not os.path.exists(res_path):
        os.mkdir(res_path)
    html_path = os.path.join(res_path, video_name + ".html")
    log_path = os.path.join(res_path, video_name + ".log")
    with open(html_path, "w", encoding='utf-8') as file:
        s = "".join(html)
        file.write(s)
        print('captions saved to ' + html_path)
        print(s+'\n')
    with open(log_path, "w", encoding='utf-8') as file:
        s = "".join(txt)
        file.write(s)
        print('captions saved to ' + log_path)
        print(s+'\n')

if __name__ == "__main__":
    material_lst = os.listdir("RESULT")
    dirazations_dir = [os.path.join("RESULT", f, "diarizations") for f in material_lst]
    for ddir in dirazations_dir:
        dirazation_files = [os.path.join(ddir, f) for f in os.listdir(ddir) if f.endswith('.txt')]
        for file in dirazation_files:
            parse_dira(file)
