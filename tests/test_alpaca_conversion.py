"""Verify the ASCOM Alpaca device layer.

Part 1 drives real devices through devices/alpaca_driver.py.
Part 2 checks that every PascalCase ASCOM member the device layer touches
actually exists on the corresponding alpyca class.

Needs the ASCOM Alpaca Simulators running:

    ./ascom.alpaca.simulators --urls http://127.0.0.1:11111

Run from the repo root:

    python3 tests/test_alpaca_conversion.py [host:port]
"""
import re
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import numpy as np
from devices import alpaca_driver

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:11111"
fails = []

print("=" * 70)
print("PART 1 - live device round-trip against %s" % HOST)
print("=" * 70)

# camera: the exact sequence devices/camera.py's _ascom_* backend performs
cam = alpaca_driver.dispatch("alpaca://%s/camera/0" % HOST)
cam.Connected = True
print("camera Connected       :", cam.Connected)
print("camera size            : %d x %d" % (cam.CameraXSize, cam.CameraYSize))
print("camera CCDTemperature  :", cam.CCDTemperature)
cam.BinX, cam.BinY = 1, 1
cam.StartExposure(0.2, True)                 # _ascom_expose
deadline = time.time() + 30
while not cam.ImageReady:                    # _ascom_imageavailable
    time.sleep(0.1)
    if time.time() > deadline:
        fails.append("camera exposure never became ready")
        break
img = np.asarray(cam.ImageArray)             # _ascom_getImageArray
print("image                  : %s %s (min %s max %s)" % (img.shape, img.dtype, img.min(), img.max()))
if img.shape != (cam.CameraXSize, cam.CameraYSize):
    fails.append("image shape %s != sensor %s" % (img.shape, (cam.CameraXSize, cam.CameraYSize)))

mnt = alpaca_driver.dispatch("alpaca://%s/telescope/0" % HOST)
mnt.Connected = True
print("mount RA/Dec           : %.4f %.4f" % (mnt.RightAscension, mnt.Declination))
print("mount Slewing/Tracking : %s %s" % (mnt.Slewing, mnt.Tracking))

foc = alpaca_driver.dispatch("alpaca://%s/focuser/0" % HOST)
foc.Connected = True
start = foc.Position
foc.Move(start + 100)
time.sleep(2)
print("focuser                : %d -> %d" % (start, foc.Position))
if foc.Position == start:
    fails.append("focuser did not move")

fw = alpaca_driver.dispatch("alpaca://%s/filterwheel/0" % HOST)
fw.Connected = True
fw.Position = 1
time.sleep(1)
print("filterwheel            : %s at %d" % (fw.Names, fw.Position))

rot = alpaca_driver.dispatch("alpaca://%s/rotator/0" % HOST)
rot.Connected = True
print("rotator                : pos %s target %s" % (rot.Position, rot.TargetPosition))

# the retarget devices/rotator.py needs in place of driver.replace('Rotator','Telescope')
tel_url = alpaca_driver.with_device_type("alpaca://%s/rotator/0" % HOST, "telescope")
rot_tel = alpaca_driver.dispatch(tel_url)
rot_tel.Connected = True
print("rotator's telescope    : %s -> %s" % (tel_url, rot_tel.Connected))

# COM ProgIDs must be refused clearly rather than failing obscurely
for bad in ["ASCOM.QHYCCD.Camera", "Maxim.CCDCamera", "COM6"]:
    try:
        alpaca_driver.dispatch(bad)
        fails.append("%s was not rejected" % bad)
    except alpaca_driver.DriverNotSupported:
        pass
print("COM ProgIDs rejected   : yes")

print()
print("=" * 70)
print("PART 2 - static member coverage")
print("=" * 70)

# Members belonging to Maxim DL / TheSkyX / native-ZWO proprietary APIs rather
# than to ASCOM.  alpyca cannot expose them, and the branches that use them are
# gated off in this build, so their absence is expected, not a defect.
# (In filter_wheel.py's Maxim branch `self.filter` is itself a Maxim camera
# object, which is why camera-ish names show up under filterwheel.)
VENDOR_ONLY = {
    "camera": {"LinkEnabled", "TemperatureSetpoint", "Temperature",
               "RegulateTemperature", "Expose", "Abort", "SetFullFrame",
               "Subframe", "AutoSaveOn", "AutoSavePath", "LastImageFileName"},
    "filterwheel": {"LinkEnabled", "TemperatureSetpoint", "CoolerOn", "Filter",
                    "GuiderFilter", "FilterIndexZeroBased"},
    "focuser": {"Link"},          # pre-ASCOM connect fallback; Alpaca always has Connected
    "telescope": set(),
    "rotator": set(),
}

OBJ_TO_CLS = {
    "camera": "camera", "mount": "telescope", "focuser": "focuser",
    "rotator": "rotator", "filter": "filterwheel",
    "filter_front": "filterwheel", "filter_back": "filterwheel",
    "camera_update_wincom": "camera", "mount_update_wincom": "telescope",
    "focuser_update_wincom": "focuser", "filterwheel_update_wincom": "filterwheel",
    "rotator_telescope": "telescope",
}

pat = re.compile(r"self\.(%s)\.([A-Z][A-Za-z0-9_]*)" % "|".join(OBJ_TO_CLS))
used = {}
for f in sorted((REPO / "devices").glob("*.py")):
    for obj, member in pat.findall(f.read_text()):
        used.setdefault(OBJ_TO_CLS[obj], set()).add(member)

for devtype in sorted(used):
    have = set(dir(alpaca_driver.DEVICE_CLASSES[devtype]))
    vendor = sorted(m for m in used[devtype] if m not in have and m in VENDOR_ONLY[devtype])
    missing = sorted(m for m in used[devtype] if m not in have and m not in VENDOR_ONLY[devtype])
    present = len(used[devtype]) - len(vendor) - len(missing)
    print("\n%-12s %2d ASCOM members used, %2d present" % (devtype, len(used[devtype]) - len(vendor), present))
    if vendor:
        print("   vendor-only, gated off (expected absent): %s" % ", ".join(vendor))
    if missing:
        print("   MISSING FROM ALPYCA: %s" % ", ".join(missing))
        fails.append("%s missing: %s" % (devtype, ", ".join(missing)))

print()
print("=" * 70)
if fails:
    print("FAILURES (%d):" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ALL CHECKS PASSED")
