# Photon Ranch Dimension Point (`DPO17`)

Runs `obs.py` on Linux with every device driven over ASCOM Alpaca, against local
stand-ins for the Photon Ranch cloud services. No traffic reaches LCO.

## What it talks to

Everything below is LCOGT handler code running locally against DynamoDB Local
(`127.0.0.1:8001`) via `PTR/ptr-local-stack`, not a reimplementation.

| Port | Service | Repo |
|---|---|---|
| 8091 | config API | `PTR/photonranch-api` |
| 8092 | status (enclosure, weather, site status) | `PTR/photonranch-status` |
| 8093 | jobs (the command queue obs.py polls) | `PTR/photonranch-jobs` |
| 8094 | calendar | `PTR/photonranch-calendar` |
| 8095 | projects | `PTR/photonranch-projects` |
| 8090 | **only** `/logs/newlog` | `PTR/ptr-api-stub` (no LCOGT repo implements it) |
| 11111 | devices | ASCOM Alpaca Simulators |

No traffic reaches LCO.

## Bringing it up

    # 1. devices
    cd ~/alpacasim/ascom.alpaca.simulators.linux-x64
    ./ascom.alpaca.simulators --urls http://127.0.0.1:11111 &

    # 2. config API (needs DynamoDB Local on 8001 first)
    cd ~/PTR/photonranch-api && python3 local_api.py &

    # 3. status / jobs / calendar / projects (real LCOGT handlers)
    cd ~/PTR/ptr-local-stack && ./run_stack.sh start && python3 seed_status.py DPO

    # 3b. the stub, for /logs/newlog only
    cd ~/PTR/ptr-api-stub && setsid nohup node ./server.js >> stub.log 2>&1 < /dev/null &

    # 4. register the WEMA config this obs belongs to, once
    curl -X PUT --data-binary @wema-dpo.json http://127.0.0.1:8091/DPO/config

    # 5. run
    cd ~/PTR/ptr-observatory && ./.venv/bin/python obs.py

`.env` supplies the endpoints — copy `.env.example` and set the `PTR_*_ROOT`
variables as described there. Without them the code defaults to LCO production,
which is exactly what you do not want on a dev box.

## How this site gets selected

`ptr_config.py` looks for a `hostname*` file in the directory **above** the repo,
so `~/PTR/hostnamedpo17.txt` selects `configs/dpo17`. Without it, it falls back to the
first three characters of the machine's hostname.

## The WEMA config

`obs.py` fetches `{PTR_API_ROOT}/{wema_name}/config/` at startup and reads
`configuration.events`, latitude, longitude and elevation from it. `configs/dpo17`
uses `wema_name = 'DPO'`, so a `DPO` entry must exist in the config API. Step 4 is
only needed when the WEMA is not running; ptr-wema publishes its own config.
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
