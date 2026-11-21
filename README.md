# Circuit · Mech Royale

Python 3.13 game bot for the Builders Buildathon, using the supplied Mech Royale Python wrapper and example decision loop. The runtime uses only the standard library. The event mounts the arena from the starter kit at /arena.

From this repository, with the extracted kit alongside it:

```sh
python3 ../mechfight-kit/check/check.py -- python3 -Bu bot.py
docker build --platform linux/amd64 -t circuit .
python3 ../mechfight-kit/check/check.py --map-dir /arena -- docker run --rm -i --platform linux/amd64 --network none --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/../mechfight-kit/arena:/arena:ro" circuit
```

Candidate A tests obstacle-aware ground navigation with the starter equipment policy. The checker replays observations. Official matches determine placement.
