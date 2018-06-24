#!/usr/bin/python
# -*- coding: utf-8 -*-
## Copyright (c) 2017, The Sumokoin Project (www.sumokoin.org)

from __future__ import print_function

#!/usr/bin/python
# -*- coding: utf-8 -*-
## Copyright (c) 2017, The Sumokoin Project (www.sumokoin.org)
'''
Process managers for lottod, lotto-wallet-cli and lotto-wallet-rpc
'''

import sys, os
import re
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
from multiprocessing import Process, Event
from time import sleep
from uuid import uuid4
from settings import RPC_DAEMON_PORT

from utils.logger import log, LEVEL_DEBUG, LEVEL_ERROR, LEVEL_INFO

from rpc import WalletRPCRequest

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0  # disable creating the window
DETACHED_PROCESS = 0x00000008  # forcing the child to have no console at all

class ProcessManager(Thread):
    def __init__(self, proc_args, proc_name=""):
        Thread.__init__(self)

        args_array = proc_args.encode( sys.getfilesystemencoding() ).split(u' ')
        i = 0
        while i < len(args_array):
                args_array[i] = args_array[i].replace('__SPACE_REPLACE__', ' ')
                i += 1

        print(args_array)
        self.proc = Popen(args_array,
                          shell=False,
                          stdout=PIPE, stderr=STDOUT, stdin=PIPE,
                          creationflags=CREATE_NO_WINDOW)
        self.proc_name = proc_name
        self.daemon = True
        log("[%s] started" % proc_name, LEVEL_INFO, self.proc_name)

    def run(self):
        for line in iter(self.proc.stdout.readline, b''):
            log(">>> " + line.rstrip(), LEVEL_DEBUG, self.proc_name)

        if not self.proc.stdout.closed:
            self.proc.stdout.close()

    def send_command(self, cmd):
        self.proc.stdin.write( (cmd + "\n").encode("utf-8") )
        sleep(0.1)

    def stop(self):
        if self.is_proc_running():
            self.send_command('exit')
            #self.proc.stdin.close()
            counter = 0
            while True:
                if self.is_proc_running():
                    if counter < 10:
                        if counter == 2:
                            try:
                                self.send_command('exit')
                            except:
                                pass
                        sleep(1)
                        counter += 1
                    else:
                        self.proc.kill()
                        log("[%s] killed" % self.proc_name, LEVEL_INFO, self.proc_name)
                        break
                else:
                    break
        log("[%s] stopped" % self.proc_name, LEVEL_INFO, self.proc_name)

    def is_proc_running(self):
        return (self.proc.poll() is None)


class ElectroneumdManager(ProcessManager):
    def __init__(self, resources_path, log_level=0, block_sync_size=10):
        resources_path = resources_path.replace(' ' ,'__SPACE_REPLACE__')
        proc_args = u'%s/bin/lottod --log-level %d --block-sync-size %d --rpc-bind-port %d' % (resources_path, log_level, block_sync_size, RPC_DAEMON_PORT)
        ProcessManager.__init__(self, proc_args, "lottod")
        self.synced = Event()
        self.stopped = Event()

    def run(self):
#         synced_str = "You are now synchronized with the network"
        err_str = "ERROR"
        for line in iter(self.proc.stdout.readline, b''):
#             if not self.synced.is_set() and line.startswith(synced_str):
#                 self.synced.set()
#                 log(synced_str, LEVEL_INFO, self.proc_name)
            if err_str in line:
                self.last_error = line.rstrip()
                log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_ERROR, self.proc_name)
            else:
                log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_INFO, self.proc_name)

        if not self.proc.stdout.closed:
            self.proc.stdout.close()

        self.stopped.set()

class WalletCliManager(ProcessManager):
    fail_to_connect_str = "wallet failed to connect to daemon"

    def __init__(self, resources_path, wallet_file_path, wallet_log_path, restore_wallet=False):
        resources_path = resources_path.replace(' ' ,'__SPACE_REPLACE__')
        wallet_file_path  = wallet_file_path.replace(' ' ,'__SPACE_REPLACE__')
        wallet_log_path  = wallet_log_path.replace(' ' ,'__SPACE_REPLACE__')
        if not restore_wallet:
            wallet_args = u'%s/bin/lotto-wallet-cli --generate-new-wallet=%s --create-address-file --log-file=%s' \
                                                % (resources_path, wallet_file_path, wallet_log_path)
        else:
            wallet_args = u'%s/bin/lotto-wallet-cli --log-file=%s --restore-deterministic-wallet --restore-height=0 --create-address-file' \
                                                % (resources_path, wallet_log_path)
        ProcessManager.__init__(self, wallet_args, "lotto-wallet-cli")
        self.ready = Event()
        self.last_error = ""

    def run(self):
        is_ready_str = "Background refresh thread started"
        err_str = "Error:"
        for line in iter(self.proc.stdout.readline, b''):
            if not self.ready.is_set() and is_ready_str in line:
                self.ready.set()
                log("Wallet ready!", LEVEL_INFO, self.proc_name)
            elif err_str in line:
                self.last_error = line.rstrip()
                log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_ERROR, self.proc_name)
#             else:
#                 log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_DEBUG, self.proc_name)

        if not self.proc.stdout.closed:
            self.proc.stdout.close()

    def is_ready(self):
        return self.ready.is_set()


    def is_connected(self):
        self.send_command("refresh")
        if self.fail_to_connect_str in self.last_error:
            return False
        return True



class WalletRPCManager(ProcessManager):
    def __init__(self, resources_path, wallet_file_path, wallet_password, app, log_level=2):
        self.user_agent = str(uuid4().hex)
        wallet_log_path = os.path.join(os.path.dirname(wallet_file_path), "lotto-wallet-rpc.log")
        resources_path = resources_path.replace(' ' ,'__SPACE_REPLACE__')
        wallet_file_path  = wallet_file_path.replace(' ' ,'__SPACE_REPLACE__')
        wallet_log_path = wallet_log_path.replace(' ' ,'__SPACE_REPLACE__')
        wallet_rpc_args = u'%s/bin/lotto-wallet-rpc --disable-rpc-login --wallet-file %s --log-file %s --rpc-bind-port %d --log-level %d --daemon-port %d --password %s' % (resources_path, wallet_file_path, wallet_log_path, RPC_DAEMON_PORT+2, log_level, RPC_DAEMON_PORT, wallet_password)

        ProcessManager.__init__(self, wallet_rpc_args, "lotto-wallet-rpc")

        self.rpc_request = WalletRPCRequest(app, self.user_agent)

        self.ready = False

        self.block_height = 0
        self.is_password_invalid = Event()

    def run(self):
        is_ready_str = "Run net_service loop"
        err_str = "ERROR"
        invalid_password = "invalid password"
        height_regex = re.compile(r"(Skipped block by timestamp, height:|Skipped block by height:|Skipped block by height:|Processed block: \<([a-z0-9]+)\>, height) (\d+)")

        for line in iter(self.proc.stdout.readline, b''):
            if not self.ready and is_ready_str in line:
                self.ready = True
                log("Wallet RPC ready!", LEVEL_INFO, self.proc_name)
            elif err_str in line:
                self.last_error = line.rstrip()
                log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_ERROR, self.proc_name)
                if not self.is_password_invalid.is_set() and invalid_password in self.last_error:
                    self.is_password_invalid.set()
            else:
                log("[%s]>>> %s" % (self.proc_name, line.rstrip()), LEVEL_DEBUG, self.proc_name)

            m_height = height_regex.search(line)
            if m_height:
                self.block_height = m_height.group(3)

        if not self.proc.stdout.closed:
            self.proc.stdout.close()

    def is_ready(self):
        return self.ready

    def is_invalid_password(self):
        return self.is_password_invalid.is_set()

    def stop(self):
        self.rpc_request.stop_wallet()
        if self.is_proc_running():
            counter = 0
            while True:
                if self.is_proc_running():
                    if counter < 5:
                        sleep(1)
                        counter += 1
                    else:
                        self.proc.kill()
                        log("[%s] killed" % self.proc_name, LEVEL_INFO, self.proc_name)
                        break
                else:
                    break
        self.ready = False
        log("[%s] stopped" % self.proc_name, LEVEL_INFO, self.proc_name)
