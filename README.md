# Circuit · Mech Royale

Python 3.13 game bot for the Builders Buildathon, using the supplied Mech Royale Python wrapper and example decision loop. The runtime uses only the standard library. The event mounts the arena from the starter kit at /arena.

From this repository, with the extracted kit alongside it:

```sh
python3 ../mechfight-kit/check/check.py -- python3 -Bu bot.py
docker build --platform linux/amd64 -t circuit .
python3 ../mechfight-kit/check/check.py --map-dir /arena -- docker run --rm -i --platform linux/amd64 --network none --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/../mechfight-kit/arena:/arena:ro" circuit
```

Candidate A tests obstacle-aware ground navigation with the starter equipment policy. The checker replays observations. Official matches determine placement.

## Practice rounds

| Git tag | Change to compare |
| --- | --- |
| round-a | Ground routes and recovery after stalled movement, with the starter equipment policy |
| round-b | Short detours for early cubes or crates and ranked upgrade choices |
| round-c | Stateful arm-gun and lightning controls with reload and visibility checks |
| round-d | Health recovery and uncontested supply drops |

Use the full commit ID from `git rev-parse round-a` (or the relevant round) in the submission form. Record the result and current qualification line after each 48-match batch. When a change lowers the score, branch from the better round and cherry-pick the next policy change, resolving the equipment and objective hooks against that base before testing. Round C and D currently include the earlier candidates’ features.

The ground-grid cache is generated from the public starter arena. Startup checks the mounted files and movement config against its fingerprint. A different map or rule set triggers an in-memory rebuild. To regenerate it locally, run `python3 tools/bake.py ../mechfight-kit`.

Run policy scenarios using `python3 -m unittest discover -s tests -v`. Set MECHFIGHT_KIT when the supplied kit is in a different directory.
