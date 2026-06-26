# mp4m-pi5.py — Pi 5 / Wayland adaptation of mp4museum.py
#
# Changes from original mp4museum.py:
#   - Removed RPi.GPIO (not supported on Pi 5 RP1; controlled via SSH/Web UI instead)
#   - Removed ALSA audio explicit device (-A alsa) -> let VLC auto-detect (PipeWire)
#   - Added --vout wl_dmabuf for Wayland (Bookworm default on Pi 5)
#   - Added --codec avcodec for HEVC support
#   - Changed media path from /media/*/ to /home/mon/playlist/
#   - Set WAYLAND_DISPLAY and XDG_RUNTIME_DIR env vars for headless Wayland session
#   - Reuse single MediaPlayer across all files to avoid window flash on transitions

import time, vlc, os, glob, logging, signal, sys

PLAYLIST_DIR = '/home/mon/playlist'
LOG_FILE = '/home/mon/vlc.log'
PID_FILE = '/home/mon/mp4m-pi5.pid'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(message)s',
)

def _cleanup(signum, frame):
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, _cleanup)
signal.signal(signal.SIGINT, _cleanup)

with open(PID_FILE, 'w') as f:
    f.write(str(os.getpid()))

# Wayland session vars (same as vlc_play_list.sh in parent project)
os.environ.setdefault('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
os.environ.setdefault('WAYLAND_DISPLAY', 'wayland-0')

# VLC instance with Pi 5 / Wayland options
instance = vlc.Instance(
    '--no-osd', '-q',
    '--vout', 'wl_dmabuf',
    '--codec', 'avcodec',
    '--image-duration', '10',
)

# Single player reused for all files — window stays open, no flash on file transitions.
# Creating a new player per file (original pattern) causes windowed flash before
# set_fullscreen(True) takes effect. Reusing the player avoids recreating the window.
player = instance.media_player_new()
player.set_fullscreen(True)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}

logging.info(f'mp4m-pi5.py started on {os.uname().nodename}')

while True:
    files = sorted(glob.glob(f'{PLAYLIST_DIR}/*.*'))
    played_any = False
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in IMAGE_EXTS:
            # wl_dmabuf cannot display raw image frames; convert to HEVC first
            logging.warning(f'Skipped (convert to HEVC first): {os.path.basename(f)}')
            continue
        played_any = True
        logging.info(f'Playing: {os.path.basename(f)}')
        media = instance.media_new(f)
        player.set_media(media)
        player.play()
        time.sleep(0.5)
        while player.get_state() in (vlc.State.Playing, vlc.State.Buffering, vlc.State.Opening):
            time.sleep(0.05)
        media.release()
    if not played_any:
        time.sleep(5)
