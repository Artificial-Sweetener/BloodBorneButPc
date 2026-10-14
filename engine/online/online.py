# SPDX-License-Identifier: GPL-2.0-or-later
"""The single INI online profile and automatically generated game host override."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

GAME_STATUS_ORIGIN = 'https://ss4.scej-network.jp:20443'
# Messages, bloodstains and ghosts: Bloodborne's own game server. shadNet servers only sign in and
# match players (co-op); the public one has no game server, so The Hunter's Dream is the default.
HUNTERS_DREAM = 'https://thehuntersdream.com'
# The game PUTs its play logs to FromSoftware's S3 buckets (bucket names nobody here owns); the game
# server takes them on its API port instead (PUT /<date>/<file>, plain HTTP), as bbhost sends them
# (droogie/bbhost src/hle/http.cpp).
PLAY_LOG_HOSTS = ('bb-playlog-prod.s3.amazonaws.com', 'bb-playlog-test.s3.amazonaws.com')
GAME_API_PORT = 18671
# P2P (co-op) port when none is set: the PS4's own, so UPnP and firewall rules stay the same
# between games.
DEFAULT_P2P_PORT = 3658
# Seconds a summon sign entry waits for its host (the game's 180; engine/online_fixes.cpp).
DEFAULT_SIGN_TIMEOUT = 30
ONLINE_ENV = ('BB_ONLINE', 'BB_SHADNET_SERVER', 'BB_SHADNET_WEBAPI', 'BB_SHADNET_NPID',
              'BB_SHADNET_PASSWORD', 'BB_SHADNET_TOKEN', 'BB_UPNP', 'SHADPS4_P2P_PORT', 'SHADPS4_HTTP_HOST_OVERRIDES_JSON',
              'BB_SIGN_TIMEOUT', 'SHADPS4_P2P_PORT_DEFAULT')

def read_settings(path):
    settings = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if line.lstrip().startswith(('#', ';')):
            continue
        key, sep, value = line.partition('=')
        if sep:
            settings[key.strip()] = value.strip()
    return settings

def game_server(text):
    """The game server as typed: empty is The Hunter's Dream, a bare name gets https://. A
    server without a port keeps the game's own (20443)."""
    text = (text or '').strip()
    if not text:
        return HUNTERS_DREAM
    if '://' not in text:
        text = 'https://' + text
    # Earlier versions defaulted to the shadNet Web API, which has no game server.
    if urlsplit(text).hostname == 'srv.shadps4.net':
        return HUNTERS_DREAM
    return text

def http_base(text):
    if not text or any(ord(c) < 32 for c in text):
        raise ValueError('Online requires an explicit WebAPI / game API URL')
    value = urlsplit(text)
    if value.scheme not in ('http', 'https') or not value.hostname or value.username is not None or value.password is not None or value.query or value.fragment:
        raise ValueError('Online API must be an HTTP(S) URL without credentials, query or fragment')
    if value.port is not None and not 1 <= value.port <= 65535:
        raise ValueError('Invalid online API port')
    return text.rstrip('/')

# The Hunter's Dream co-op pool (online_pool=huntersdream), with bbhost's players: bbbridge
# (MaskZeus, GPL-3.0-or-later, bbbridge/ in the package) stands in for the shadNet server on this PC
# and talks to The Hunter's Dream the way bbhost does. Its account (Discord sign-in) and settings
# live in network/bbbridge/, which updates keep.
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 31313
BRIDGE_WEBAPI = f'http://{BRIDGE_HOST}:31315'
# The game's own server traffic, through the bridge's proxies (bbbridge src/setup.cpp).
BRIDGE_OVERRIDES = {
    GAME_STATUS_ORIGIN: f'http://{BRIDGE_HOST}:31316',
    'https://thehuntersdream.com:20443': f'http://{BRIDGE_HOST}:31316',
    'https://thehuntersdream.com:18671': f'http://{BRIDGE_HOST}:31317',
    'http://thehuntersdream.com:18671': f'http://{BRIDGE_HOST}:31317',
    'https://bb-playlog-test.s3.amazonaws.com:443': f'http://{BRIDGE_HOST}:31317',
    'https://bb-playlog-prod.s3.amazonaws.com:443': f'http://{BRIDGE_HOST}:31317',
    'https://thehuntersdream.com:18671/summon_messenger': BRIDGE_WEBAPI,
    'http://thehuntersdream.com:18671/summon_messenger': BRIDGE_WEBAPI,
}

def bridge_folder(data):
    """network/bbbridge with bbbridge's settings file pointing at its account file there.
    Returns (folder, settings file)."""
    folder = Path(data) / 'network' / 'bbbridge'
    folder.mkdir(parents=True, exist_ok=True)
    config = folder / 'bbbridge_config.json'
    wanted = {'state_file': str((folder / 'bbbridge_state.json').resolve())}
    try:
        current = json.loads(config.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        current = {}
    if not isinstance(current, dict):
        current = {}
    if any(current.get(k) != v for k, v in wanted.items()):
        config.write_text(json.dumps({**current, **wanted}, indent=2) + '\n', encoding='utf-8')
    return folder, config

def bridge_accounts(data):
    """The Hunter's Dream accounts signed in on this PC (bbbridge's account file)."""
    try:
        state = json.loads((Path(data) / 'network/bbbridge/bbbridge_state.json').read_text(encoding='utf-8'))
        return list(state.get('accounts', {}))
    except (OSError, ValueError, AttributeError):
        return []

def configure_hunters_dream(settings, data, env):
    accounts = bridge_accounts(data)
    if not accounts:
        raise ValueError("The Hunter's Dream: sign in with Discord on the launcher's Online page first")
    wanted = settings.get('online_thd_account', '')
    destination = Path(data) / 'network/host_overrides.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(BRIDGE_OVERRIDES, indent=2), encoding='utf-8')
    os.replace(temporary, destination)
    env.update(BB_ONLINE='1', BB_BRIDGE='1', BB_SHADNET_SERVER=f'{BRIDGE_HOST}:{BRIDGE_PORT}',
               BB_SHADNET_WEBAPI=BRIDGE_WEBAPI,
               BB_SHADNET_NPID=wanted if wanted in accounts else accounts[0],
               # The game signs in with a password; the bridge never reads it.
               BB_SHADNET_PASSWORD='bbbridge',
               BB_UPNP='1' if settings.get('online_upnp') == '1' else '0',
               SHADPS4_HTTP_HOST_OVERRIDES_JSON=str(destination.resolve()),
               # The bridge sends the other players' traffic to this port: no fallback to another.
               SHADPS4_P2P_PORT=str(DEFAULT_P2P_PORT), SHADPS4_P2P_PORT_DEFAULT='0')
    timeout = settings.get('online_sign_timeout', '').strip()
    env['BB_SIGN_TIMEOUT'] = str(min(max(int(timeout), 0), 600)) if timeout.isdigit() else str(DEFAULT_SIGN_TIMEOUT)
    return destination

# Online play is paused while the connection is reworked together with The Hunter's Dream team: the
# game stays offline whatever bbport.ini says (BB_ONLINE_PAUSED=0 lifts it, for that work).
ONLINE_PAUSED = os.environ.get('BB_ONLINE_PAUSED', '1') != '0'


def configure_online(settings, data, env):
    env.pop('BB_BRIDGE', None)
    if ONLINE_PAUSED and settings.get('online_enabled') == '1':
        print("Online: paused in this version while we rework the connection together with The Hunter's "
              'Dream team; the game starts offline', flush=True)
    if (ONLINE_PAUSED or settings.get('online_enabled') != '1' or
            settings.get('online_connected', '1') != '1'):
        for key in ONLINE_ENV:
            env.pop(key, None)
        env['BB_ONLINE'] = '0'
        return None
    if settings.get('online_pool') == 'huntersdream':
        return configure_hunters_dream(settings, data, env)
    host = settings.get('online_host', '').strip().strip('[]')
    if not host or any(c.isspace() or ord(c) < 32 for c in host) or any(c in host for c in '/@?#:'):
        raise ValueError('Enter a shadNet server before enabling online')
    port = int(settings.get('online_port', ''))
    if not 1 <= port <= 65535:
        raise ValueError('shadNet TCP port must be between 1 and 65535')
    webapi = http_base(settings.get('online_webapi', '').strip() or f'http://{host}:31315')
    game_api = http_base(game_server(settings.get('online_game_api', '')))
    if urlsplit(webapi).path not in ('', '/') or urlsplit(game_api).path not in ('', '/'):
        raise ValueError('WebAPI and game API require a server origin without an extra path')
    username = settings.get('online_username', '')
    if not 1 <= len(username.encode('utf-8')) <= 16 or any(c.isspace() or ord(c) < 32 for c in username):
        raise ValueError('Enter the shadNet account name (up to 16 characters)')
    if not env.get('BB_SHADNET_PASSWORD'):
        raise ValueError('Sign in with the account password in the launcher')
    p2p = settings.get('online_p2p_port', '').strip()
    if p2p and not 1 <= int(p2p) <= 65535:
        raise ValueError('Local P2P port must be between 1 and 65535, or empty for the default (3658)')
    # Runtime cache only. Never read or overwrite another application's JSON,
    # and never route private-server traffic through a public server by default.
    destination = Path(data) / 'network/host_overrides.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.json.tmp')
    overrides = {GAME_STATUS_ORIGIN: game_api}
    overrides.update({h: f'http://{urlsplit(game_api).hostname}:{GAME_API_PORT}' for h in PLAY_LOG_HOSTS})
    temporary.write_text(json.dumps(overrides, indent=2), encoding='utf-8')
    os.replace(temporary, destination)
    env.update(BB_ONLINE='1', BB_SHADNET_SERVER=(f'[{host}]' if ':' in host else host) + f':{port}',
               BB_SHADNET_WEBAPI=webapi, BB_SHADNET_NPID=username,
               BB_UPNP='1' if settings.get('online_upnp') == '1' else '0',
               SHADPS4_HTTP_HOST_OVERRIDES_JSON=str(destination.resolve()))
    env['SHADPS4_P2P_PORT'] = str(int(p2p)) if p2p else str(DEFAULT_P2P_PORT)
    # The default may be taken or reserved on this PC: the engine falls back to a free port then.
    # A port the player set is kept as it is.
    env['SHADPS4_P2P_PORT_DEFAULT'] = '0' if p2p else '1'
    timeout = settings.get('online_sign_timeout', '').strip()
    env['BB_SIGN_TIMEOUT'] = str(min(max(int(timeout), 0), 600)) if timeout.isdigit() else str(DEFAULT_SIGN_TIMEOUT)
    return destination
