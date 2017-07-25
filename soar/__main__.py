#!/usr/bin/env python3
""" Soar v0.11.0 command line entrypoint.

Allows use of Soar from the command line by passing arguments to :func:`soar.client.main.main`.
"""
from sys import exit
from argparse import ArgumentParser

from soar.client.main import main as invoke_client


def main():
    parser = ArgumentParser(prog='soar', description='SoaR v0.11.0\nSnakes on a Robot: An extensible Python framework '
                                                     'for simulating and interacting with robots')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--quicktime', action='store_true', help='Run quickly, without sleeping between steps',
                        dest='quicktime')
    parser.add_argument('--logfile', type=str, help='Log file to write to', required=False)
    parser.add_argument('-s', metavar='step duration', type=float, help='The duration of a controller step', required=False,
                        default=0.1, dest='step_duration')
    parser.add_argument('-b', '-brain', metavar='brain', type=str, help='Path to the brain file', required=False,
                        dest='brain_path')
    parser.add_argument('-w', '-world', metavar='world', type=str, help='Path to the world file', required=False,
                        dest='world_path')
    args = parser.parse_args()
    return_val = invoke_client(brain_path=args.brain_path, world_path=args.world_path, headless=args.headless,
                               logfile=args.logfile, step_duration=args.step_duration, realtime=not args.quicktime)
    exit(return_val)

if __name__ == '__main__':
    main()
