import subprocess
import tqdm
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read all podcast urls
url_books = open("url_books.txt", "r")
urls = url_books.readlines()
url_books.close()

def download_podcast(url):
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", url])

new_lines = []
# Download relevant podcasts
for url in tqdm.tqdm(urls):
    if url[0] == '!':
        new_lines.append(url)
        continue
    if url[0] == '#':
        os.chdir(BASE_DIR)
        se = url[1:].strip()
        se_path = os.path.join(BASE_DIR, se)
        if not os.path.exists(se_path):
            os.mkdir(se_path)
        if not os.path.exists(os.path.join(se_path, "original_soundtrack")):
            os.mkdir(os.path.join(se_path, "original_soundtrack"))
        os.chdir(os.path.join(se_path, "original_soundtrack"))
    if url[0] != '#':
        print("Downloading podcast from " + url)
        try:
            download_podcast(url)
            # add ! to the beginning of the line to skip downloading the podcast
            url = "!" + url
        except:
            print("Failed to download podcast from {} in {}".format(url, se))
    new_lines.append(url)
    
# Update the url_books file
os.chdir(BASE_DIR)
url_books = open("url_books.txt", "w")
url_books.writelines(new_lines)