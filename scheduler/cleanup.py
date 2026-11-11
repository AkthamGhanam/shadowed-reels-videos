"""Delete video files from the `videos` branch once YouTube has them (queue item has a videoId).
Run from a checkout of the videos branch in ./vids; marks items with removed=true in the queue."""
import json, os, subprocess
Q = 'scheduler/queue.json'
q = json.load(open(Q)); gone = []
for it in q:
    if it.get('videoId') and not it.get('removed'):
        p = os.path.join('vids', it['file'])
        if os.path.exists(p):
            subprocess.run(['git', '-C', 'vids', 'rm', '-q', it['file']], check=True); gone.append(it['file'])
        it['removed'] = True
json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
print('removed', gone)
