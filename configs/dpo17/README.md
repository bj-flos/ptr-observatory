# Dimension Point Observatory (`DPO-17`)

The observatory half of the Dimension Point site: `obs.py` on Linux with every
device driven over ASCOM Alpaca, against a local Photon Ranch stack. No traffic
reaches LCO.

This directory is a **config template**, not a deployment. It stays lowercase
(`dpo17`) because that is what `OBS_CONFIG_TEMPLATE` names; the site id it
produces is `DPO-17`, and all four simulated sites are built from this same
template with their own place and policy layered on.

## How it actually runs

In a container, alongside its wema, both supervised. See the `ptr-site`
repository:

    cd ptr-site
    docker compose --env-file sites/dimension-point.env \
                   --env-file sites/secrets.local.env up -d

That container runs four processes: the ASCOM Alpaca Simulators, Sky Simulator,
the wema and this observatory. `configure_site.py` copies this template to
`configs/DPO-17` and appends the site's own values from the environment, so the
template is the source of truth for the hardware and the env file for the
place.

Nothing is started by hand any more. Earlier versions of this file described
launching the services and simulators individually on the host; that is no
longer how it works, and following it now would collide with the running stack
on every port.

## What it talks to

Backend services on the shared `ptr-net` network, reached by name — see
`ptr-services`:

| Port | Service | Repo |
|---|---|---|
| 8091 | config API | `photonranch-api` |
| 8092 | status | `photonranch-status` |
| 8093 | jobs — the command queue this polls | `photonranch-jobs` |
| 8094 | calendar | `photonranch-calendar` |
| 8095 | projects | `photonranch-projects` |
| 8090 | `/logs/newlog` only | `ptr-api-stub` |

Devices are two Alpaca servers inside the container:

| Port | Server | Devices |
|---|---|---|
| 11112 | Sky Simulator | mount, camera, guider, focuser, rotator, filter wheel |
| 11111 | ASCOM Alpaca Simulators | dome, observing conditions, safety monitor — the wema's |

`OBS_ALPACA_URL` and `WEMA_ALPACA_URL` select which each config faces; both
fall back to `ALPACA_URL`, so a site with one server needs only that.

## How this config is selected

`ptr_config.py` reads a `hostname*` file in the directory above the repo, so
`/app/hostnameDPO-17.txt` selects `configs/DPO-17`. The entrypoint writes it.

Note the asymmetry between the two programs, which is easy to trip over:
`ptr-observatory` takes the name from that file **verbatim**, while `ptr-wema`
**lowercases** `PTR_WEMA_SITE` before looking for `configs/<name>`. Rendering
a config to the wrong case leaves the program loading the shipped template with
none of the site's values applied, and nothing says so.

## The wema config

`obs.py` fetches `{PTR_API_ROOT}/{wema_name}/config/` at startup and reads
`configuration.events`, latitude, longitude and elevation from it. This site
uses `wema_name = 'DPO'`, so a `DPO` entry must exist in the config API — the
wema publishes its own on startup, so in normal operation there is nothing to
do. `wema-dpo.json` here is only for standing the obs up without its wema.
`ptr_events.Events` does have a fallback, but it puts the site at
Pacific/Midway.
