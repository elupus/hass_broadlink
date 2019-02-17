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

Installation
------------
Install all files in a "hass_broadlink" subdirectory of .homeassistant/custom_components. For example like:

.. code-block:: bash
    cd .homeassistant
    mkdir custom_components
    git clone https://github.com/elupus/hass_broadlink.git

Make sure the component irgen is installed in your python environment running home assistant:
.. code-block:: bash
    pip install git+https://github.com/elupus/irgen.git#egg=irgen

Add media_player block to your configuration.


Example Configuration
-------

.. code-block:: yaml

    media_player:

      - platform: hass_broadlink
        host: 192.168.0.2
        mac: '00:00:00:00:00:00'
        name: 'Yamaha RXV1400'

        command_on:
          code: [nec1, 122, -1, 29]
          delay: 2.0 # Delay until next command is accepted

        command_off: [nec1, 122, -1, 30]

        volume_up: [nec1, 122, -1, 26]
        volume_down: [nec1, 122, -1, 27]
        volume_mute: [nec1, 122, -1, 128]
        volume_mute_on: [nec1, 126, -1, 162]
        volume_mute_off: [nec1, 126, -1, 163]

        next_track: [nec1, 122, -1, 16]
        previous_track: [nec1, 122, -1, 17]

        # To support volume control by sliders, your media_player must be able to change to a fixed volume
        # with an ir code. For example using some type of state restore.
        volume_set:
          # Volume to restore device to when turned on, to know state
          restore: -40

          # If player only display volume on first button press. Configure this value
          # to the number of seconds this volume activation remains in effect
          timeout: 3.0

          # Level on device that represent 0% volume
          min: -80.0

          # Level on device that represent 100% volume
          max: 0.0

          # Change in level on device on each volume_up or volume_down
          step: 0.5

          # Ircodes for fixed volume levels. It's enough with a single level for this to work.
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