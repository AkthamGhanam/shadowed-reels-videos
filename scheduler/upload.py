"""Free YouTube scheduler for The Shadowed Reels.
Reads scheduler/queue.json, uploads pending videos with the YouTube Data API
(scheduled via status.publishAt), posts the first comment once each video is live,
and writes the results back to queue.json.
Secrets (GitHub repo -> Settings -> Secrets -> Actions): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import json, os, sys, tempfile, datetime as dt, urllib.request, urllib.parse, urllib.error

Q = os.path.join(os.path.dirname(__file__), 'queue.json')
RAW = 'https://raw.githubusercontent.com/AkthamGhanam/shadowed-reels-videos/videos/'
MAX_UPLOADS = int(os.environ.get('MAX_UPLOADS', '4'))  # quota: ~1600 units per upload, 10000/day
CATEGORY = {'ENTERTAINMENT': '24', 'FILM_ANIMATION': '1'}

def now(): return dt.datetime.now(dt.timezone.utc)

def req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()

def token():
    body = urllib.parse.urlencode({'client_id': os.environ['YT_CLIENT_ID'], 'client_secret': os.environ['YT_CLIENT_SECRET'],
                                   'refresh_token': os.environ['YT_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    s, _, b = req('https://oauth2.googleapis.com/token', body, {'Content-Type': 'application/x-www-form-urlencoded'})
    if s != 200: sys.exit(f'token error {s}: {b[:300]}')
    return json.loads(b)['access_token']

def upload(tok, it):
    pub = dt.datetime.fromisoformat(it['publishAt'])
    status = {'selfDeclaredMadeForKids': False, 'embeddable': True}
    if pub > now() + dt.timedelta(minutes=15):
        status.update(privacyStatus='private', publishAt=pub.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    else:
        status['privacyStatus'] = 'public'
    meta = {'snippet': {'title': it['title'][:100], 'description': it.get('description', ''), 'tags': it.get('tags', []),
                        'categoryId': CATEGORY.get(it.get('category', 'ENTERTAINMENT'), '24')}, 'status': status}
    path = tempfile.mktemp(suffix='.mp4')
    urllib.request.urlretrieve(RAW + it['file'], path)
    size = os.path.getsize(path)
    s, h, b = req('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                  json.dumps(meta).encode(), {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json; charset=UTF-8',
                                              'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    loc = {k.lower(): v for k, v in h.items()}.get('location')
    if s != 200 or not loc: raise RuntimeError(f'init {s}: {b[:400]}')
    with open(path, 'rb') as f:
        s, _, b = req(loc, f.read(), {'Authorization': f'Bearer {tok}', 'Content-Type': 'video/mp4'}, 'PUT')
    os.remove(path)
    if s not in (200, 201): raise RuntimeError(f'upload {s}: {b[:400]}')
    v = json.loads(b)
    return v['id'], v.get('status', {}).get('privacyStatus')

def comment(tok, vid, text):
    body = {'snippet': {'videoId': vid, 'topLevelComment': {'snippet': {'textOriginal': text}}}}
    s, _, b = req('https://www.googleapis.com/youtube/v3/commentThreads?part=snippet', json.dumps(body).encode(),
                  {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})
    if s != 200: raise RuntimeError(f'comment {s}: {b[:300]}')
    return json.loads(b)['id']

def main():
    q = json.load(open(Q))
    tok = token(); done = 0
    for it in sorted(q, key=lambda i: i['publishAt']):
        if it.get('skip'): continue
        if not it.get('videoId') and dt.datetime.fromisoformat(it['publishAt']) < now() - dt.timedelta(hours=2):
            it['skip'] = 'missed'; print('missed', it['title']); continue
        if not it.get('videoId') and done < MAX_UPLOADS:
            try:
                it['videoId'], it['privacy'] = upload(tok, it); it['uploadedAt'] = now().isoformat(); it.pop('error', None); done += 1
                print('uploaded', it['title'], it['videoId'])
            except Exception as e:
                it['error'] = str(e)[:500]; print('FAILED', it['title'], e)
                if 'quotaExceeded' in str(e): break
        elif it.get('videoId') and it.get('comment') and not it.get('commentId') and dt.datetime.fromisoformat(it['publishAt']) <= now():
            try: it['commentId'] = comment(tok, it['videoId'], it['comment']); print('commented', it['title'])
            except Exception as e: it['commentError'] = str(e)[:300]
    json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)

if __name__ == '__main__': main()
