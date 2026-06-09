# config.example.py
#
# Copy this file to `config.py` and adjust the values for your machine.
# `config.py` is git-ignored, so your personal/local paths never get committed.
#
#   cp config.example.py config.py   (or copy it in Explorer)

# Full path to the Open Rails executable.
OPENRAILS_EXE = r"C:\Path\To\Open Rails\OpenRails.exe"

# Directory where Open Rails writes its PhysicalInfoDump<port>.csv log files.
OR_LOG_DIR = r"C:\Path\To\Open Rails\Program\Logs"

# Directory where Ray Tune stores training results and checkpoints.
RESULTS_DIR = r"C:\Path\To\results"

# Base HTTP API port. Worker i listens on BASE_PORT + i.
BASE_PORT = 2149

# In-sim time acceleration factor (the thesis v3 agent used 8).
TIME_SPEED = 8
