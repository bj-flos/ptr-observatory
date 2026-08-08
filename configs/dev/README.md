# Linux dev site (`dev1`)

Runs `obs.py` on Linux with every device driven over ASCOM Alpaca, against local
stand-ins for the Photon Ranch cloud services. No traffic reaches LCO.

## What it talks to

| Service | Where | What it is |
|---|---|---|
| config API | `127.0.0.1:8091` | `PTR/photonranch-api/local_api.py` — LCOGT's **real** `api.site_configs` handlers over DynamoDB Local (`127.0.0.1:8001`) |
| status, jobs, logs, calendar, projects | `127.0.0.1:8090` | `PTR/ptr-api-stub` — inert stand-ins; separate services in production, not part of photonranch-api |
| devices | `127.0.0.1:11111` | ASCOM Alpaca Simulators (camera, telescope, focuser, filter wheel, rotator) |

## Bringing it up

    # 1. devices
    cd ~/alpacasim/ascom.alpaca.simulators.linux-x64
    ./ascom.alpaca.simulators --urls http://127.0.0.1:11111 &

    # 2. config API (needs DynamoDB Local on 8001 first)
    cd ~/PTR/photonranch-api && python3 local_api.py &

    # 3. the other services
    cd ~/PTR/ptr-api-stub && setsid nohup node ./server.js >> stub.log 2>&1 < /dev/null &

    # 4. register the WEMA config this obs belongs to, once
    curl -X PUT --data-binary @wema-dev.json http://127.0.0.1:8091/dev/config

    # 5. run
    cd ~/PTR/ptr-observatory && ./.venv/bin/python obs.py

`.env` supplies the endpoints — copy `.env.example` and set the `PTR_*_ROOT`
variables as described there. Without them the code defaults to LCO production,
which is exactly what you do not want on a dev box.

## How this site gets selected

`ptr_config.py` looks for a `hostname*` file in the directory **above** the repo,
so `~/PTR/hostnamedev.txt` selects `configs/dev`. Without it, it falls back to the
first three characters of the machine's hostname.

## The WEMA config

`obs.py` fetches `{PTR_API_ROOT}/{wema_name}/config/` at startup and reads
`configuration.events`, latitude, longitude and elevation from it. `configs/dev`
uses `wema_name = 'dev'`, so a `dev` entry must exist in the config API — see step 4.
`ptr_events.Events` does have a fallback, but it puts the site at Pacific/Midway.

## Devices

All four are Alpaca URLs pointing at the simulators:

    mount        alpaca://127.0.0.1:11111/telescope/0
    focuser      alpaca://127.0.0.1:11111/focuser/0
    filter wheel alpaca://127.0.0.1:11111/filterwheel/0
    camera       alpaca://127.0.0.1:11111/camera/0

The rotator is left unassigned (`main_rotator: None`), matching tbo2. Point it at
`alpaca://127.0.0.1:11111/rotator/0` to exercise it.

## Not yet exercised

Device init and the main loop work. The FITS upload path and the subprocess
pipeline (platesolve, SEP, smartstacks) have not been run here.
