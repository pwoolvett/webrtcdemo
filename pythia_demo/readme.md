1. Uninstall Kivy-Jetson and install Kivy
    `python3 -m pip uninstall Kivy-Jetson`
    `python3 -m pip install Kivy`

2. Reinstall pyds_ext
    `python3 -m pip install --upgrade pip`
    `python3 -m pip uninstall pyds_ext`
    `git clone -m https://github.com/rmclabs-io/pyds_ext && cd pyds_ext && python3 -m pip install .`

3. Reinstall 