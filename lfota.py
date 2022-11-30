#!/usr/bin/python3

#
# SPDX-License-Identifier: MIT
#
# Copyright (c) 2022 Kontron Electronics GmbH
# Author: Frieder Schrempf
#

from argparse import ArgumentParser
from pathlib import Path
from serial import Serial
import os
import re
import sys
import time

AT_BAUDRATE = 9600

class clr:
    OK = '\033[92m'
    INFO = '\033[94m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'

parser = ArgumentParser(
    description="Update SIMCom module firmware via serial connection"
)
parser.add_argument('--show', action='store_true',
                    help='show model and firmware information')
parser.add_argument('--update', action='store_true',
                    help='perform FOTA update from local file')
parser.add_argument('device',
                    help='serial device for AT commands and FOTA file upload')
parser.add_argument('file', nargs='?',
                    help='path to diff file with FOTA update')

args = parser.parse_args()

if args.update and args.file is None:
    parser.error("--update requires to set a path to a diff file")

def atcommand(serial, cmd, timeout=1, log=False, parse=[], continuous=False):
    data = {}
    status = -1
    serial.write(f"{cmd}\r".encode())
    time.sleep(timeout)
    while (parse != None and serial.in_waiting > 0):
        recv = serial.readline().decode().rstrip('\n')
        if (log):
            print(recv)
        for value in parse:
            if (recv.startswith(f"{value}: ")):
                val = recv.lstrip(f"${parse}: ").rstrip('\r')
                data[re.sub('\W+','', value).lower()] = val
        if recv == 'OK\r':
            status = 0
    if not continuous and parse != None and status != 0:
        print(f"{clr.FAIL}AT command '{cmd}' returned error!{clr.RESET}")
        return status
    return data

if (args.show):
    serial = Serial(args.device, AT_BAUDRATE, timeout=1)
    ati = atcommand(serial, 'ATI', parse=['Model', 'Revision'])
    fw_gmr = atcommand(serial, 'AT+CGMR', parse=['+CGMR'])
    fw_sub = atcommand(serial, 'AT+CSUB', parse=['+CSUB'])
    if ati == -1 or fw_gmr == -1 or fw_sub == -1:
        sys.exit(1)

    print(
        f"Model {clr.INFO}{ati['model']}{clr.RESET} with "
        f"HW revision {clr.INFO}{ati['revision']}{clr.RESET} and "
        f"FW revision {clr.INFO}{fw_gmr['cgmr']}/{fw_sub['csub']}{clr.RESET} detected"
    )
elif (args.update):
    serial = Serial(args.device, AT_BAUDRATE, timeout=1)
    path = Path(args.file)
    if (not path.is_file):
        print(f"{clr.FAIL}Failed to find firmware file {args.file}!{clr.RESET}")
        sys.exit(1)

    fw_gmr = atcommand(serial, 'AT+CGMR', parse=['+CGMR'])
    fw_sub = atcommand(serial, 'AT+CSUB', parse=['+CSUB'])
    if fw_gmr == -1 or fw_sub == -1:
        sys.exit(1)

    fw_before = f"{fw_gmr['cgmr']}/{fw_sub['csub']}"
    print(f"FW revision {clr.INFO}{fw_before}{clr.RESET} detected")

    file_len = os.path.getsize(path)
    ret = atcommand(serial, f"AT+LFOTA=0,{file_len}")
    if (ret == -1):
        sys.exit(1)

    atcommand(serial, f"AT+LFOTA=1,{file_len}", continuous=True)

    print(f"{clr.INFO}Sending update file", end='', flush=True)

    try:
        with open(path, "rb") as f:
            i = 0
            # Read blocks of 265 bytes from the update file and write them
            # to the serial interface. Wait for 50 ms between each block as
            # specified by the manufacturer.
            while (bytes := f.read(256)):
                serial.write(bytes)
                if (i % 10 == 0):
                    print(f".{clr.RESET}", end='', flush=True)
                i += 1
                time.sleep(0.05)
    except:
        print(f"{clr.FAIL}\nFailed to write firmware file!{clr.RESET}")
        sys.exit(1)

    print(f"{clr.RESET}")
    time.sleep(5)

    lfota = atcommand(serial, f"AT+LFOTA?", parse=['+LFOTA'])
    if lfota == -1:
        sys.exit(1)
    elif lfota['lfota'] != '1':
        print(f"{clr.FAIL}\nAT+LFOTA? returns status {lfota['lfota']}!{clr.RESET}")
        sys.exit(1)

    time.sleep(1)

    # Perform reset without reading back from the serial interface as it might
    # already be down when we try to do so.
    ret = atcommand(serial, 'AT+CRESET', parse=None)
    if (ret == -1):
        sys.exit(1)

    serial.close()
    time.sleep(1)

    # Restart serial connection after reset
    print(
        f"{clr.INFO}Wait for module to reset and TTY to reappear, "
        f"this can take a while...{clr.RESET}"
    )
    i = 0
    while (not serial.is_open and i < 100):
        try:
            i += 1
            serial = Serial(args.device, AT_BAUDRATE, timeout=1)
        except:
            time.sleep(1)
            pass

    if (not serial.is_open):
        print(f"{clr.FAIL}TTY device not available after reset!{clr.RESET}")
        sys.exit(1)

    time.sleep(5)

    fw_gmr = atcommand(serial, 'AT+CGMR', parse=['+CGMR'])
    fw_sub = atcommand(serial, 'AT+CSUB', parse=['+CSUB'])
    if fw_gmr == -1 or fw_sub == -1:
        sys.exit(1)

    fw_after = f"{fw_gmr['cgmr']}/{fw_sub['csub']}"

    if fw_before == fw_after:
        print(
            f"{clr.FAIL}Firmware update failed, version is still: "
            f"{fw_after} (same as before the update)!{clr.RESET}"
        )
        sys.exit(1)

    print(
        f"{clr.OK}Firmware update succeeded, new version: {fw_after}{clr.RESET}"
    )
else:
    parser.print_usage()
