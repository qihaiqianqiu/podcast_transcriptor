# 播客/视频转录工程
1. youtube-dl下载原音频
2. pyannote识别演讲者并且切分音频
3. whisper large-v3模型 speech to context
4. transformer某NLP模型翻译中文
5. 生成对白式HTML文稿
# Requirements
**pyannote**
```pip install pyannote.audio```
**whisper**
```pip install -U openai-whisper```
```sudo apt update && sudo apt install ffmpeg```
```pip install setuptools-rust```
