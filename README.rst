********************************
Broadlink IR transmitter media_player component for home-assistant
********************************


Component
======

This is a custom component for `Home Assistant <https://home-assistant.io/>`__ providing
alternate versions of the built in broadlink component


Media Player
------------

Media player with support for simpler setup of control of a media player. It among other things support
generation of IR sequences using a (protocol, device, subdevice, function) tuple as retrieved from 
https://irdb.tk/.

Example Configuration
-------

.. code-block:: yaml

    media_player:

      - platform: hass_broadlink
        host: 192.168.0.2
        mac: '00:00:00:00:00:00'
        name: 'Yamaha RXV1400'

        command_on: [nec1, 122, -1, 29]
        command_off: [nec1, 122, -1, 30]

        volume_up: [nec1, 122, -1, 26]
        volume_down: [nec1, 122, -1, 27]
        volume_mute: [nec1, 122, -1, 128]
        volume_mute_on: [nec1, 126, -1, 162]
        volume_mute_off: [nec1, 126, -1, 163]

        digitdelay: 0.0

        volume_set:
          # If player only display volume on first button press. Configure this value
          # to the number of seconds this volume activation remains in effect
          timeout: 3.0
          min: -80.0
          max: 0.0
          step: 0.5
          levels:
            -40.0: [nec1, 126, -1, 117]

        sources:
          tuner: [nec1, 122 ,-1, 22]
          dtv: [nec1, 122, -1, 84]
          dvd: [nec1, 122, -1, 193]
          cd: [nec1, 122 ,-1, 21]

        sound_modes:
          straight:      [nec1, 126, -1, 224]
          pl2_movie:     [nec1, 126, -1, 103]
          pl2_music:     [nec1, 126, -1, 104]
          neo6_movie:    [nec1, 126, -1, 105]
          neo6_music:    [nec1, 126, -1, 106]
          6ch_stereo:    [nec1, 126, -1, 255] 