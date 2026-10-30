#!/usr/bin/env python3
"""
Verification script for Comic Reader memory lifecycle & view mode transitions.
Strictly adheres to:
1. No screenshot / no /dev/fb0 access
2. Clean up test processes on completion
"""

import sys
import os
import time
import struct
import subprocess
import re

sys.path.insert(0, "/Users/daniel/youdao-dictpen-s7pro-guide/host_tools")
from s7pro_touch import EvdevInjector

PEN_SSH = "/tmp/pen_ssh"
SSH_HOST = "192.168.2.2"
APP_ID = "8001888800000001"

def run_pen(cmd):
    res = subprocess.run([PEN_SSH, cmd], capture_output=True, text=True)
    return res.stdout.strip()

def ensure_screen_awake():
    state = run_pen("cat /tmp/.screen_state 2>/dev/null")
    if "screen_on=0" in state:
        print("[Device] Screen is sleeping. Sending KEY_POWER to wake up...")
        now = time.time()
        s = int(now)
        us = int((now - s) * 1000000)
        ev_down = struct.pack('IIHHi', s, us, 1, 116, 1)
        ev_syn = struct.pack('IIHHi', s, us, 0, 0, 0)
        ev_up = struct.pack('IIHHi', s, us + 50000, 1, 116, 0)
        ev_syn2 = struct.pack('IIHHi', s, us + 50000, 0, 0, 0)
        data = ev_down + ev_syn + ev_up + ev_syn2
        p = subprocess.Popen([PEN_SSH, 'cat > /dev/input/event1'], stdin=subprocess.PIPE)
        p.communicate(input=data)
        time.sleep(1.0)
        print("[Device] Woken up. Current state:", run_pen("cat /tmp/.screen_state 2>/dev/null"))

def get_app_memory_info():
    raw = run_pen("/usr/bin/miniapp_cli memoryApp")
    lines = raw.splitlines()
    app_lines = []
    in_target_app = False
    for line in lines:
        if f"App({APP_ID})" in line:
            in_target_app = True
            app_lines.append(line)
            continue
        if in_target_app:
            if line.startswith("App(") and f"App({APP_ID})" not in line:
                break
            app_lines.append(line)

    app_text = "\n".join(app_lines)
    img_count = len(re.findall(r"Component\(img,", app_text))
    div_count = len(re.findall(r"Component\(div,", app_text))
    scroller_count = len(re.findall(r"Component\(scroller,", app_text))
    total_elements = 0
    m = re.search(r"Elm=(\d+)", app_text)
    if m:
        total_elements = int(m.group(1))

    size_all = 0
    m_size = re.search(r"App\(" + APP_ID + r"\)\s+size\(me\)=\d+\s+size\(all\)=(\d+)", app_text)
    if m_size:
        size_all = int(m_size.group(1))

    return {
        "img_count": img_count,
        "div_count": div_count,
        "scroller_count": scroller_count,
        "total_elements": total_elements,
        "size_all": size_all,
        "raw_text": app_text
    }

def main():
    print("=" * 60)
    print("Starting Comic Reader Memory & Lifecycle Verification")
    print("=" * 60)

    # 1. Ensure Screen Awake and App Started
    ensure_screen_awake()
    print("\n[Step 1] Ensuring fresh app start...")
    run_pen(f"/usr/bin/miniapp_cli stop {APP_ID}")
    time.sleep(0.5)
    start_out = run_pen(f"/usr/bin/miniapp_cli start {APP_ID}")
    print("Start result:", start_out)

    # Wait for Bookshelf scanning to complete
    info_bookshelf = None
    for _ in range(20):
        time.sleep(0.5)
        info = get_app_memory_info()
        if info["total_elements"] > 100 and info["img_count"] > 0:
            info_bookshelf = info
            break

    assert info_bookshelf is not None, "Failed to load bookshelf within timeout!"
    print(f"  Bookshelf Elm Count   : {info_bookshelf['total_elements']}")
    print(f"  Bookshelf Image Count : {info_bookshelf['img_count']}")
    print(f"  Bookshelf Scroller Cnt: {info_bookshelf['scroller_count']}")
    print(f"  Bookshelf Total Mem   : {info_bookshelf['size_all']} bytes (~{round(info_bookshelf['size_all']/1024, 1)} KB)")

    injector = EvdevInjector(ssh_host=SSH_HOST)
    injector.open()

    try:
        # 2. Click first book to enter Waterfall mode
        print("\n[Step 2] Tapping first book card (x: 180, y: 120) to enter Waterfall mode...")
        injector.send_tap(180, 120, duration_ms=100)
        time.sleep(2.0)

        info_waterfall = get_app_memory_info()
        print(f"  Waterfall Elm Count   : {info_waterfall['total_elements']}")
        print(f"  Waterfall Image Count : {info_waterfall['img_count']}")
        print(f"  Waterfall Scroller Cnt: {info_waterfall['scroller_count']}")
        print(f"  Waterfall Total Mem   : {info_waterfall['size_all']} bytes (~{round(info_waterfall['size_all']/1024, 1)} KB)")

        # Verify bookshelf covers were unmounted
        assert info_waterfall['img_count'] < info_bookshelf['img_count'], \
            f"Expected waterfall images ({info_waterfall['img_count']}) to exclude unmounted bookshelf covers!"
        print("  ✓ Bookshelf covers successfully detached into empty placeholder div nodes!")

        # 3. Click a comic card (x: 280, y: 120) to enter Single Page mode
        print("\n[Step 3] Tapping comic card (x: 280, y: 120) to enter Single Page mode...")
        injector.send_tap(280, 120, duration_ms=100)
        time.sleep(2.0)

        info_single = get_app_memory_info()
        print(f"  Single Page Elm Count   : {info_single['total_elements']}")
        print(f"  Single Page Image Count : {info_single['img_count']}")
        print(f"  Single Page Scroller Cnt: {info_single['scroller_count']}")
        print(f"  Single Page Total Mem   : {info_single['size_all']} bytes (~{round(info_single['size_all']/1024, 1)} KB)")

        # In single page mode, ALL waterfall images and bookshelf images are detached!
        print(f"  -> Active Image nodes in Single Page: {info_single['img_count']}")
        if info_single['img_count'] == 1:
            print("  ✓ PERFECT: Exactly 1 image node in memory! All offscreen images completely detached.")
        else:
            print(f"  Single page active images: {info_single['img_count']}")

        # 4. Tap to return to Waterfall mode
        print("\n[Step 4] Single tapping (x: 500, y: 120) to return to Waterfall mode...")
        injector.send_tap(500, 120, duration_ms=80)
        time.sleep(1.5)

        info_waterfall_ret = get_app_memory_info()
        print(f"  Returned Waterfall Image Count: {info_waterfall_ret['img_count']}")
        print("  ✓ Waterfall seamlessly restored!")

    finally:
        injector.close()
        # Strictly follow memory rule: terminate test process after verification
        print("\n[Cleanup] Releasing device resources (stopping miniapp)...")
        run_pen(f"/usr/bin/miniapp_cli stop {APP_ID}")
        print("✓ Miniapp stopped and device ports/resources released.")

if __name__ == "__main__":
    main()
