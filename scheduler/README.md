# YouTube scheduler (free)

`queue.json` lists the videos to publish. Every hour, GitHub Actions runs `upload.py`, which:
- uploads every pending video whose `publishAt` is still ahead, as private with `publishAt`, so YouTube makes it public at that time;
- posts the `comment` as the first comment once the video is live (pinning it is done by hand in Studio, the API cannot pin);
- skips anything more than 2 hours late, marking it `"skip": "missed"`;
- writes back `videoId`, `privacy`, `error`, `commentId`.

Video files are read from the `videos` branch (`file` is the path there).
Required secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
To run it right away: Actions → YouTube scheduler → Run workflow.
