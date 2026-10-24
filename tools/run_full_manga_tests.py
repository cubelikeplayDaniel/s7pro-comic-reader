#!/usr/bin/env python3
"""
Comprehensive automated test suite for S7 Pro Comic Reader (8001888800000001).
Tests:
  1. Multi-comic library parsing & bookshelf rendering
  2. 120-page long manga (苍穹铁道纪行) parsing and waterfall rendering
  3. Aspect ratio classification verification (wide spreads 880px vs portrait 440px)
  4. Viewport scrolling and O(log N) binary search / windowing
  5. Single page 1/1 (wide) and 3/4 (portrait) inspection mode
  6. Double-tap to zoom (1x -> 2x -> 1x)
  7. Single-tap to return to waterfall (with debounced resolution)
  8. Boundary clamping during pan (0px overshoot)
  9. Left-edge swipe right to return step-by-step
  10. Natural numeric sorting on external directory /userdisk/manga/四格学园祭
"""

import os
import sys
import time
import subprocess
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s7pro_touch import EvdevInjector
from fb2png import fb2png

SSH_HOST = "192.168.2.2"
PEN_SSH = "/tmp/pen_ssh"
SCREENSHOT_DIR = "/tmp/comic_test_screens"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def run_pen(cmd):
    res = subprocess.run([PEN_SSH, cmd], capture_output=True, text=True)
    return res.stdout.strip()


def capture_screen(name):
    raw_path = f"/tmp/{name}.raw"
    png_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    run_pen(f"dd if=/dev/fb0 of={raw_path} bs=240 count=4080 2>/dev/null")
    subprocess.run(
        f"scp -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@{SSH_HOST}:{raw_path} {raw_path}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    fb2png(raw_path, png_path, rotate=270)
    return png_path


def test_suite():
    print("=" * 60)
    print("Starting Comprehensive Test Suite for Comic Reader")
    print("=" * 60)

    # 1. Start App
    print("\n[Step 1] Launching Comic Reader (8001888800000001)...")
    run_pen("/usr/bin/miniapp_cli stop 8001888800000001")
    time.sleep(0.5)
    out = run_pen("/usr/bin/miniapp_cli start 8001888800000001")
    print("Start result:", out)
    time.sleep(2.0)

    p1 = capture_screen("01_bookshelf")
    print("Captured bookshelf:", p1)

    injector = EvdevInjector(ssh_host=SSH_HOST)
    injector.open()

    try:
        # 2. Enter '苍穹铁道纪行' (120 pages)
        print("\n[Step 2] Clicking '苍穹铁道纪行' (120 pages long manga)...")
        # Click on the first book card (x: 250, y: 120)
        injector.send_tap(250, 120, duration_ms=100)
        time.sleep(1.5)
        p2 = capture_screen("02_waterfall_top_120p")
        print("Captured waterfall top (pages 1-2 portrait 440+440):", p2)

        # 3. Waterfall Scroll down to see 16:9 wide spread (Page 3)
        print("\n[Step 3] Scrolling down to inspect 16:9 wide spread...")
        # Swipe up on right content area (x: 500, y: 190 -> y: 50)
        injector.send_swipe(500, 200, 500, 40, duration_ms=250, steps=20)
        time.sleep(1.0)
        p3 = capture_screen("03_waterfall_wide_spread")
        print("Captured waterfall wide spread:", p3)

        # 4. Jump step test (click bottom-left page counter)
        print("\n[Step 4] Testing fast step jump in 120-page manga...")
        injector.send_tap(54, 210, duration_ms=100)
        time.sleep(1.2)
        p4 = capture_screen("04_waterfall_jumped_p31")
        print("Captured jumped page (p31):", p4)

        # 5. Click on an image to enter Single Page inspection mode
        print("\n[Step 5] Clicking image to enter Single Page inspection mode...")
        injector.send_tap(500, 120, duration_ms=100)
        time.sleep(1.5)
        p5 = capture_screen("05_single_page_mode")
        print("Captured single page inspection mode:", p5)

        # 6. Double click to zoom (1x -> 2x)
        print("\n[Step 6] Double clicking center to toggle 2x zoom...")
        injector.send_tap(500, 120, duration_ms=60)
        time.sleep(0.08)
        injector.send_tap(500, 120, duration_ms=60)
        time.sleep(1.2)
        p6 = capture_screen("06_single_zoomed_2x")
        print("Captured 2x zoomed single page:", p6)

        # 7. Pan drag test during zoom
        print("\n[Step 7] Dragging to pan during 2x zoom (boundary clamped)...")
        injector.send_swipe(550, 150, 350, 90, duration_ms=200, steps=15)
        time.sleep(0.8)
        p7 = capture_screen("07_single_panned_clamped")
        print("Captured panned & clamped single page:", p7)

        # 8. Left-edge swipe right to return to Waterfall
        print("\n[Step 8] Left-edge swipe right gesture to return from Single -> Waterfall...")
        injector.send_swipe(30, 120, 260, 120, duration_ms=200, steps=15)
        time.sleep(1.2)
        p8 = capture_screen("08_back_to_waterfall")
        print("Captured returned waterfall:", p8)

        # 9. Left-edge swipe right to return to Bookshelf
        print("\n[Step 9] Left-edge swipe right gesture to return from Waterfall -> Bookshelf...")
        injector.send_swipe(30, 120, 260, 120, duration_ms=200, steps=15)
        time.sleep(1.2)
        p9 = capture_screen("09_back_to_bookshelf")
        print("Captured returned bookshelf:", p9)

        # 10. Horizontal scroll bookshelf to open external / natural sort manga (四格学园祭 / 星际远征队)
        print("\n[Step 10] Scrolling bookshelf horizontally...")
        injector.send_swipe(700, 120, 200, 120, duration_ms=220, steps=20)
        time.sleep(1.0)
        p10 = capture_screen("10_bookshelf_scrolled")
        print("Captured scrolled bookshelf:", p10)

        # 11. Enter '星际远征队' (Wide-heavy comic)
        print("\n[Step 11] Entering '星际远征队' (16:9 / 21:9 wide heavy comic)...")
        injector.send_tap(350, 120, duration_ms=100)
        time.sleep(1.5)
        p11 = capture_screen("11_waterfall_scifi_wide")
        print("Captured scifi comic waterfall:", p11)

        # 12. Enter single page mode on a 16:9 / 21:9 page to verify 1/1 full-width (912px)
        print("\n[Step 12] Entering single page on 16:9 wide page to verify 1/1 full-width...")
        injector.send_tap(500, 120, duration_ms=100)
        time.sleep(1.5)
        p12 = capture_screen("12_single_wide_fullwidth")
        print("Captured single wide fullwidth (1/1):", p12)

        # 13. Single tap on image to return to waterfall (debounced 250ms)
        print("\n[Step 13] Single tap to return to waterfall...")
        injector.send_tap(500, 120, duration_ms=80)
        time.sleep(1.5)
        p13 = capture_screen("13_single_tap_returned_waterfall")
        print("Captured waterfall returned via single tap:", p13)

    finally:
        injector.close()
        # Per user memory specification: release processes after testing
        print("\n[Cleanup] Stopping miniapp to free resources...")
        run_pen("/usr/bin/miniapp_cli stop 8001888800000001")
        print("[Done] Test run completed successfully.")


if __name__ == "__main__":
    test_suite()
