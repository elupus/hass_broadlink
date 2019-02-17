
"""
Support for broadlink remote control of a media device.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.broadlink/
"""

import asyncio
from base64 import b64decode
import binascii
import logging
import socket
from math import copysign
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL, SUPPORT_NEXT_TRACK,
    SUPPORT_PLAY_MEDIA, SUPPORT_PREVIOUS_TRACK, SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET, SUPPORT_SELECT_SOUND_MODE)
from homeassistant.const import (
    CONF_COMMAND_OFF, CONF_COMMAND_ON, CONF_HOST, CONF_MAC, CONF_NAME,
    CONF_PORT, CONF_TIMEOUT, STATE_OFF, STATE_ON)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = [
    'broadlink==0.9.0',
    'irgen==0.1.0',
]
DOMAIN = 'broadlink'

DEFAULT_NAME = "Broadlink IR Media Player"
DEFAULT_TIMEOUT = 10
DEFAULT_DELAY = 0.5
DEFAULT_PORT = 80

CONF_VOLUME_UP = 'volume_up'
CONF_VOLUME_DOWN = 'volume_down'
CONF_VOLUME_MUTE = 'volume_mute'
CONF_VOLUME_MUTE_ON = 'volume_mute_on'
CONF_VOLUME_MUTE_OFF = 'volume_mute_off'
CONF_NEXT_TRACK = 'next_track'
CONF_PREVIOUS_TRACK = 'previous_track'
CONF_SOURCES = 'sources'
CONF_CHANNELS = 'channels'
CONF_DIGITS = 'digits'
CONF_SOUND_MODES = 'sound_modes'
CONF_VOLUME_LEVELS = 'levels'
CONF_VOLUME_STEP = 'step'
CONF_VOLUME_MAX = 'max'
CONF_VOLUME_MIN = 'min'
CONF_VOLUME_SET = 'volume_set'
CONF_VOLUME_TIMEOUT = 'timeout'
CONF_VOLUME_RESTORE = 'restore'
CONF_CODE = 'code'
CONF_DELAY = 'delay'

_LOGGER = logging.getLogger(__name__)


def convert_list_to_hex(data):
    if len(data) != 4:
        raise vol.Invalid('Invalid length of list')

    import irgen
    raw = irgen.gen_raw_general(*data)
    res = irgen.gen_broadlink_base64_from_raw(raw)
    _LOGGER.debug("%s converted to: %s", data, res)
    return res


def convert_code_to_command(data):
    return {
        CONF_CODE: data,
        CONF_DELAY: None
    }


CODE_SCHEMA = vol.Schema(
    vol.Any(
        vol.All(
            list,
            convert_list_to_hex,
        ),
        cv.string
    )
)

COMMAND_SCHEMA = vol.Schema(
    vol.Any(
        {vol.Required(CONF_CODE): CODE_SCHEMA,
         vol.Optional(CONF_DELAY, default=0.0): float},
        vol.All(
            CODE_SCHEMA,
            convert_code_to_command
        )
    )
)

DIGITS_SCHEMA = vol.Schema({
    vol.Required('0'): COMMAND_SCHEMA,
    vol.Required('1'): COMMAND_SCHEMA,
    vol.Required('2'): COMMAND_SCHEMA,
    vol.Required('3'): COMMAND_SCHEMA,
    vol.Required('4'): COMMAND_SCHEMA,
    vol.Required('5'): COMMAND_SCHEMA,
    vol.Required('6'): COMMAND_SCHEMA,
    vol.Required('7'): COMMAND_SCHEMA,
    vol.Required('8'): COMMAND_SCHEMA,
    vol.Required('9'): COMMAND_SCHEMA,
})

ENTRY_SCHEMA = vol.Schema({str: COMMAND_SCHEMA})
VOLUME_LEVELS_SCHEMA = vol.Schema({float: COMMAND_SCHEMA})
VOLUME_SCHEMA_SET = vol.Schema({
    vol.Optional(CONF_VOLUME_RESTORE): float,
    vol.Required(CONF_VOLUME_MAX): float,
    vol.Required(CONF_VOLUME_MIN): float,
    vol.Required(CONF_VOLUME_LEVELS): VOLUME_LEVELS_SCHEMA,
    vol.Required(CONF_VOLUME_STEP): float,
    vol.Optional(CONF_VOLUME_TIMEOUT): float,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,

    vol.Optional(CONF_COMMAND_ON): COMMAND_SCHEMA,
    vol.Optional(CONF_COMMAND_OFF): COMMAND_SCHEMA,
    vol.Optional(CONF_VOLUME_SET): VOLUME_SCHEMA_SET,
    vol.Optional(CONF_VOLUME_UP): COMMAND_SCHEMA,
    vol.Optional(CONF_VOLUME_DOWN): COMMAND_SCHEMA,
    vol.Optional(CONF_VOLUME_MUTE): COMMAND_SCHEMA,
    vol.Optional(CONF_VOLUME_MUTE_ON): COMMAND_SCHEMA,
    vol.Optional(CONF_VOLUME_MUTE_OFF): COMMAND_SCHEMA,
    vol.Optional(CONF_NEXT_TRACK): COMMAND_SCHEMA,
    vol.Optional(CONF_PREVIOUS_TRACK): COMMAND_SCHEMA,
    vol.Optional(CONF_SOURCES, default={}): ENTRY_SCHEMA,
    vol.Optional(CONF_SOUND_MODES, default={}): ENTRY_SCHEMA,
    vol.Optional(CONF_DIGITS): DIGITS_SCHEMA,
})

SUPPORT_MAPPING = [
    (CONF_COMMAND_ON, SUPPORT_TURN_ON),
    (CONF_COMMAND_OFF, SUPPORT_TURN_OFF),
    (CONF_VOLUME_UP, SUPPORT_VOLUME_STEP),
    (CONF_VOLUME_DOWN, SUPPORT_VOLUME_STEP),
    (CONF_VOLUME_MUTE, SUPPORT_VOLUME_MUTE),
    (CONF_NEXT_TRACK, SUPPORT_NEXT_TRACK),
    (CONF_PREVIOUS_TRACK, SUPPORT_PREVIOUS_TRACK),
]


async def async_setup_platform(hass,
                               config,
                               async_add_devices,
                               discovery_info=None):
    """Set up platform."""
    import broadlink

    host = (config.get(CONF_HOST),
            config.get(CONF_PORT))
    mac = get_broadlink_mac(config.get(CONF_MAC))

    link = broadlink.rm(
        host,
        mac,
        None)

    try:
        await hass.async_add_job(link.auth)
    except socket.timeout:
        _LOGGER.warning("Timeout trying to authenticate to broadlink")
        raise PlatformNotReady

    async_add_devices([BroadlinkRM(link, config)])


def get_supported_by_config(config):
    """Calculate support flags based on available configuration entries."""
    support = 0

    for mapping in SUPPORT_MAPPING:
        if mapping[0] in config:
            support = support | mapping[1]

    if config.get(CONF_SOURCES):
        support = support | SUPPORT_SELECT_SOURCE

    if config.get(CONF_SOUND_MODES):
        support = support | SUPPORT_SELECT_SOUND_MODE

    if config.get(CONF_DIGITS):
        support = support | SUPPORT_PLAY_MEDIA

    if config.get(CONF_VOLUME_SET):
        support = support | SUPPORT_VOLUME_SET

    return support


def get_broadlink_mac(mac: str):
    """Convert a mac address string with : in it to just a flat string."""
    return binascii.unhexlify(mac.encode().replace(b':', b''))


def convert_volume_to_device(config_volume_set, volume):
    return (
        config_volume_set[CONF_VOLUME_MIN] +
        volume * (config_volume_set[CONF_VOLUME_MAX] -
                  config_volume_set[CONF_VOLUME_MIN])
    )


class BroadlinkRM(MediaPlayerDevice):
    """Representation of a media device."""

    def __init__(self, link, config):
        """Initialize device."""
        super().__init__()

        self._support = get_supported_by_config(config)
        self._config = config
        self._link = link
        self._state = STATE_OFF
        self._source = None
        self._sound_mode = None
        self._muted = None
        self._volume_level = None
        self._lock = asyncio.Lock()
        self._volume_timestamp = datetime.now() + timedelta(seconds=-100)
        self._volume_calls = 0
        self._volume_step = None
        self._volume_levels = None
        self._volume_restore = None

        if CONF_VOLUME_SET in config:
            volume_set = config[CONF_VOLUME_SET]
            scale  = (volume_set[CONF_VOLUME_MAX] -
                      volume_set[CONF_VOLUME_MIN])
            offset = volume_set[CONF_VOLUME_MIN]
            self._volume_step = volume_set[CONF_VOLUME_STEP] / scale
            self._volume_levels = {
                (level - offset) / scale: code
                for level, code in volume_set[CONF_VOLUME_LEVELS].items()
            }
            _LOGGER.debug("Converted step %f, volumes: %s",
                          self._volume_step, self._volume_levels)
            if CONF_VOLUME_RESTORE in volume_set:
                self._volume_restore = (
                    (volume_set[CONF_VOLUME_RESTORE] - offset) / scale
                )

    async def send(self, command):
        """Send b64 encoded command to device."""
        if command is None:
            raise Exception('No command defined!')

        packet = b64decode(command[CONF_CODE])
        await self.hass.async_add_job(self._link.send_data, packet)

        if command[CONF_DELAY]:
            await asyncio.sleep(command[CONF_DELAY])

    async def send_volume(self, code):
        if await self._volume_timeout():
            await self.send(code)
        await self.send(code)
        self._volume_timestamp = datetime.now()

    @property
    def name(self):
        """Return the name of the controlled device."""
        return self._config.get(CONF_NAME)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return self._support

    async def async_turn_on(self):
        """Turn on media player."""
        async with self._lock:
            await self.send(self._config.get(CONF_COMMAND_ON))
            self._state = STATE_ON

        if self._volume_restore:
            await self.async_set_volume_level(self._volume_restore)

    async def async_turn_off(self):
        """Turn off media player."""
        async with self._lock:
            await self.send(self._config.get(CONF_COMMAND_OFF))
            self._state = STATE_OFF

    async def async_volume_up(self):
        """Volume up media player."""
        async with self._lock:
            await self.send_volume(self._config.get(CONF_VOLUME_UP))

            if CONF_VOLUME_STEP in self._config and \
               self._volume_level is not None:
                self._volume_level += self._volume_step

    async def async_volume_down(self):
        """Volume down media player."""
        async with self._lock:
            await self.send_volume(self._config.get(CONF_VOLUME_DOWN))

            if CONF_VOLUME_STEP in self._config and \
               self._volume_level is not None:
                self._volume_level -= self._volume_step

    async def async_mute_volume(self, mute):
        """Send mute command."""
        async with self._lock:
            if mute and CONF_VOLUME_MUTE_ON in self._config:
                await self.send(self._config.get(CONF_VOLUME_MUTE_ON))
                self._muted = True
            elif not mute and CONF_VOLUME_MUTE_OFF in self._config:
                await self.send(self._config.get(CONF_VOLUME_MUTE_OFF))
                self._muted = False
            else:
                await self.send(self._config.get(CONF_VOLUME_MUTE))

    async def async_media_next_track(self):
        """Send next track command."""
        async with self._lock:
            await self.send(self._config.get(CONF_NEXT_TRACK))

    async def async_media_previous_track(self):
        """Send the previous track command."""
        async with self._lock:
            await self.send(self._config.get(CONF_PREVIOUS_TRACK))

    async def async_select_source(self, source):
        """Select a specific source."""
        async with self._lock:
            await self.send(self._config.get(CONF_SOURCES)[source])
            self._source = source
            self._sound_mode = None

    async def async_select_sound_mode(self, sound_mode):
        """Select a specific source."""
        async with self._lock:
            await self.send(self._config.get(CONF_SOUND_MODES)[sound_mode])
            self._sound_mode = sound_mode

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Switch to a specific channel."""
        if media_type != MEDIA_TYPE_CHANNEL:
            _LOGGER.error('Unsupported media type %s', media_type)
            return

        cv.positive_int(media_id)
        async with self._lock:
            for digit in media_id:
                await self.send(self._config.get(CONF_DIGITS).get(digit))
                await asyncio.sleep(self._config.get(CONF_DIGITDELAY))

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        if CONF_VOLUME_SET not in self._config:
            raise NotImplementedError()

        config = self._config[CONF_VOLUME_SET]

        self._volume_calls += 1
        volume_calls = self._volume_calls

        async with self._lock:
            if self._volume_calls != volume_calls:
                _LOGGER.debug('Aborted volume change early')

            def items():
                if self._volume_level:
                    yield self._volume_level, None
                yield from self._volume_levels.items()

            base_level, base_code = min(
                items(),
                key=lambda kv: abs(volume - kv[0]))

            steps = int(round((volume - base_level) / self._volume_step))
            if steps > 0:
                code = self._config.get(CONF_VOLUME_UP)
            else:
                code = self._config.get(CONF_VOLUME_DOWN)

            target = base_level + self._volume_step * steps

            _LOGGER.debug('Volume base %f(%f) target %f(%f) steps %f',
                          base_level,
                          convert_volume_to_device(config, base_level),
                          target,
                          convert_volume_to_device(config, target),
                          steps)

            # lie and say we are at volume, while
            # changing to keep gui happy
            self._volume_level = target

            if base_code:
                await self.send(base_code)
                self._volume_timestamp = datetime.now()

            for step in range(abs(steps)):
                await self.send_volume(code)
                if self._volume_calls != volume_calls:
                    _LOGGER.debug('Aborted volume change')

                    # set correct level on abort
                    self._volume_level = base_level + (
                        self._volume_step * copysign(step + 1, steps))
                    break

            _LOGGER.debug('Volume level %f(%f)',
                          self._volume_level,
                          convert_volume_to_device(config, self._volume_level))

    async def _volume_timeout(self):
        if CONF_VOLUME_TIMEOUT not in self._config[CONF_VOLUME_SET]:
            return False

        timeout = self._config[CONF_VOLUME_SET][CONF_VOLUME_TIMEOUT]
        delay = (datetime.now() - self._volume_timestamp).total_seconds()
        remain = timeout - delay

        if remain > 0.0:
            if remain < 0.5:
                _LOGGER.debug("Volume timeout %f", remain)
                await asyncio.sleep(remain)
                return True
            else:
                return False
        else:
            _LOGGER.debug("Volume timeout %f", remain)
            return True

    @property
    def media_content_type(self):
        """Return content type currently active."""
        return MEDIA_TYPE_CHANNEL

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return list(self._config.get(CONF_SOURCES).keys())

    @property
    def sound_mode(self):
        """Name of the current sound mode."""
        return self._sound_mode

    @property
    def sound_mode_list(self):
        """List of available sound modes."""
        return list(self._config.get(CONF_SOUND_MODES).keys())

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def volume_level(self):
        return self._volume_level

    @property
    def media_title(self):
        """Title of current playing media."""
        return self._source
