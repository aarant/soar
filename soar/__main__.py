#!/usr/bin/env python3
# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/__main__.py
""" Allows use of Soar from the command line by passing arguments to :func:`soar.client.main`
    ::

        usage: soar [-h] [--headless] [--nosleep] [--logfile LOGFILE]
                    [-s step duration] [-b brain] [-w world] [--options OPTIONS]

        optional arguments:
          -h, --help         show this help message and exit
          --headless         Run in headless mode
          --nosleep          Run quickly, without sleeping between steps
          --logfile LOGFILE  Log file to write to
          -s step duration   The duration of a controller step
          -b brain           Path to the brain file
          -w world           Path to the world file
          --options OPTIONS  Options to pass to the robot, as a JSON deserializable dictionary
"""
import sys
import json
from argparse import ArgumentParser

from soar import __version__, blerb
import soar.client as client


def main():
    parser = ArgumentParser(prog='soar', description=blerb)
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--nosleep', action='store_true', help='Run quickly, without sleeping between steps',
                        dest='nosleep')
    parser.add_argument('--logfile', type=str, help='Log file to write to', required=False)
    parser.add_argument('-s', metavar='step duration', type=float, help='The duration of a controller step',
                        required=False, default=0.1, dest='step_duration')
    parser.add_argument('-b', metavar='brain', type=str, help='Path to the brain file', required=False,
                        dest='brain_path')
    parser.add_argument('-w', metavar='world', type=str, help='Path to the world file', required=False,
                        dest='world_path')
    parser.add_argument('--options', type=str, help='Options to pass to the robot, as a JSON deserializable dictionary',
                        required=False)
    args = parser.parse_args()
    if args.options is not None:
        args.options = json.loads(args.options)
        assert(type(args.options) is dict)  # Make sure the options are valid
    return_val = client.main(brain_path=args.brain_path, world_path=args.world_path, headless=args.headless,
                             logfile=args.logfile, step_duration=args.step_duration, realtime=not args.nosleep,
                             options=args.options)
    sys.exit(return_val)

if __name__ == '__main__':
    main()
