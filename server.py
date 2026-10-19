import os, tempfile, shutil, re
from flask import Flask, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__, static_folder="static", static_url_path="")

@app.get("/")
def home():
    return app.send_static_file("index.html")

@app.get("/api/info")
def info():
    url = request.args.get("url", "").strip()
    if not re.match(r"^https?://", url):
        return jsonify(error="الرابط غير صالح"), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
            d = ydl.extract_info(url, download=False)
    except Exception:
        return jsonify(error="تعذر قراءة الفيديو. تأكد أن الرابط عام وصحيح."), 422
    heights = sorted({f["height"] for f in d.get("formats", [])
                      if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
    return jsonify(title=d.get("title"), thumbnail=d.get("thumbnail"),
                   uploader=d.get("uploader"), duration=d.get("duration"),
                   site=d.get("extractor_key"), heights=heights)

@app.get("/api/download")
def download():
    url = request.args.get("url", "").strip()
    kind = request.args.get("kind", "video")      # video | audio
    h = request.args.get("height", "best")
    if not re.match(r"^https?://", url):
        return jsonify(error="الرابط غير صالح"), 400
    tmp = tempfile.mkdtemp()
    opts = {"quiet": True, "noplaylist": True, "outtmpl": f"{tmp}/%(title).80s.%(ext)s"}
    if kind == "audio":
        opts.update(format="bestaudio/best", postprocessors=[
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}])
    else:
        sel = "" if h == "best" else f"[height<={int(h)}]"
        opts.update(format=f"bestvideo{sel}+bestaudio/best{sel}", merge_output_format="mp4")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        path = os.path.join(tmp, os.listdir(tmp)[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify(error="فشل التحميل"), 500

    @after_this_request
    def cleanup(resp):
        shutil.rmtree(tmp, ignore_errors=True)
        return resp
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
