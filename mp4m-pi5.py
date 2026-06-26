# mp4m-pi5.py — Pi 5 / Wayland adaptation of mp4museum.py
#
# Changes from original mp4museum.py:
#   - Removed RPi.GPIO (unsupported on Pi 5 RP1 chip; controlled via SSH/Web UI instead)
#   - Removed ALSA audio explicit device (-A alsa) -> let VLC auto-detect (PipeWire)
#   - Added --vout wl_dmabuf for Wayland (Bookworm default on Pi 5)
#   - Added --codec avcodec for HEVC support
#   - Changed media path from /media/*/ to /home/mon/playlist/
#   - Set WAYLAND_DISPLAY and XDG_RUNTIME_DIR env vars for headless Wayland session

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

# VLC instance — shared across all files (created once, reused per file)
# Original used '-q -A alsa --alsa-audio-device hw:X' per-file instance; here:
#   --vout wl_dmabuf : Wayland DMA-BUF output (Pi 5 / Bookworm required)
#   --codec avcodec  : FFmpeg decoder for broad HEVC support
#   audio omitted    : VLC auto-selects PipeWire / ALSA on Pi 5 Bookworm
instance = vlc.Instance(
    '--fullscreen', '--no-osd', '-q',
    '--vout', 'wl_dmabuf',
    '--codec', 'avcodec',
)

def vlc_play(source):
    """Play a single file and block until playback ends (mirrors original pattern)."""
    player = instance.media_player_new()
    media = instance.media_new(source)
    player.set_media(media)
    player.play()
    time.sleep(1)
    # Instance --fullscreen alone is insufficient with python-vlc; must call explicitly
    player.set_fullscreen(True)
    current_state = player.get_state()
    while current_state in (vlc.State.Playing, vlc.State.Buffering, vlc.State.Opening):
        time.sleep(0.05)
        current_state = player.get_state()
    media.release()
    player.release()


logging.info(f'mp4m-pi5.py started on {os.uname().nodename}')

# Main loop — same structure as original mp4museum.py
while True:
    files = sorted(glob.glob(f'{PLAYLIST_DIR}/*.*'))
    if not files:
        time.sleep(5)
        continue
    for f in files:
        logging.info(f'Playing: {os.path.basename(f)}')
        vlc_play(f)
