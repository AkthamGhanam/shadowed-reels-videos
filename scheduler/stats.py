#!/usr/bin/env python3
"""Reads public statistics (views, likes, comments) of every uploaded video in
the queue and writes them to scheduler/stats.json."""
import json, os, urllib.request, urllib.parse, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))

def req(url, data=None, headers=None):
    r = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read().decode())

def token():
    body = urllib.parse.urlencode(dict(client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'],
                                       refresh_token=os.environ['YT_REFRESH_TOKEN'], grant_type='refresh_token')).encode()
    return req('https://oauth2.googleapis.com/token', body, {'Content-Type': 'application/x-www-form-urlencoded'})['access_token']

def main():
    q = json.load(open(os.path.join(HERE, 'queue.json')))
    q = q if isinstance(q, list) else q.get('items', q.get('queue', []))
    extra = []
    p = os.path.join(HERE, 'extra_ids.json')
    if os.path.exists(p): extra = json.load(open(p))
    ids = [i['videoId'] for i in q if i.get('videoId')] + extra
    tok = token(); out = {}
    for k in range(0, len(ids), 50):
        u = 'https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet,status,contentDetails&maxResults=50&id=' + ','.join(ids[k:k+50])
        for v in req(u, headers={'Authorization': 'Bearer ' + tok}).get('items', []):
            s = v.get('statistics', {})
            out[v['id']] = dict(title=v['snippet']['title'], publishedAt=v['snippet']['publishedAt'],
                                privacy=v.get('status', {}).get('privacyStatus'), publishAt=v.get('status', {}).get('publishAt'),
                                duration=v.get('contentDetails', {}).get('duration'),
                                views=int(s.get('viewCount', 0)), likes=int(s.get('likeCount', 0)), comments=int(s.get('commentCount', 0)))
    json.dump(dict(updated=dt.datetime.now(dt.timezone.utc).isoformat(), videos=out), open(os.path.join(HERE, 'stats.json'), 'w'), indent=1)
    print('stats for', len(out), 'videos')

if __name__ == '__main__':
    main()
