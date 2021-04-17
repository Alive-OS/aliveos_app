# *************************************************************************
#
# Copyright (c) 2021 Andrei Gramakov. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# site:    https://agramakov.me
# e-mail:  mail@agramakov.me
#
# *************************************************************************

from rospy import logdebug, logerr, loginfo, logwarn, ServiceException, set_param, spin
from time import sleep, time
from threading import Thread
from aliveos_py import ConstantNamespace
from aliveos_py.ros import get_subscriber
from typing import Union
from .exceptions import ReceivedAbort, ReceivedBusy
from .generic_mind_node import GenericMindNode, node_types
from aliveos_msgs import msg


class EGO_COMMANDS(ConstantNamespace):
    RESET = "reset"
    PAUSE = "pause"
    CONTINUE = "continue"


class EgoNode(GenericMindNode):
    """
    This class has main function (shold be implemented) that starts with the node and works when it is not interrupted
    by other nodes
    """

    WAIT_DESCRETE_SEC = 0.05

    def __init__(self, name, concept_files: list = None):
        super().__init__(name=name, concept_files=concept_files, node_type=node_types.EGO_NODE)
        self.sub_ego_commands = None
        self.flag_pause = True
        self.flag_paused = False
        self.flag_terminate_thread = False
        self.thread_main = None  # type: Union[None, Thread]

    def _handler_pause(self):
        logdebug(f"_handler_pause {self.flag_pause}")
        while self.flag_pause:
            if self.flag_terminate_thread:
                break
            sleep(.1)

    def _handler_abort(self):
        logdebug("_handler_abort")
        self._handler_pause()
        self._main()

    def _callback_ego_commands(self, params: msg.EgoCommands):
        logdebug(f"c2c -> ego : {params.cmd}")
        if params.cmd == EGO_COMMANDS.PAUSE:
            self._pause_main()
        elif params.cmd == EGO_COMMANDS.CONTINUE:
            self._unpause_main()
        elif params.cmd == EGO_COMMANDS.RESET:
            self._restart_main()
        else:
            logwarn(f"Ego got an incorrect command: {params.cmd}")

    def _pause_main(self):
        loginfo("Ego paused")
        self.flag_pause = True

    def _unpause_main(self):
        loginfo("Ego unpaused")
        self.flag_pause = False

    def _terminate_main(self, timeout_s=10):
        if not self.thread_main:
            raise RuntimeError("Main is not started")
        self.flag_terminate_thread = True
        start_time = time()
        logdebug(f"Start time: {start_time}")
        while self.thread_main.is_alive():
            sleep(.1)
            logdebug(f"Time: {time()}")
            if time() - start_time > timeout_s:
                raise TimeoutError("Cannot terminate the main thread")
        self.flag_terminate_thread = False
        self.thread_main = None

    def _start_main(self):
        logdebug("_start_main")
        if self.thread_main:
            raise RuntimeError("Main is already started")
        self.thread_main = Thread(target=self._main)
        self.thread_main.start()

    def _restart_main(self):
        logdebug("_restart_main")
        try:
            self._terminate_main()
        except RuntimeError:
            pass
        self._start_main()

    def _main(self):
        """
        Main function supervisor
        """
        while (1):
            self._handler_pause()
            if self.flag_terminate_thread:
                break
            try:
                logwarn("Main started")
                self.main()
            except ReceivedAbort:
                loginfo("Abort")
                return

    def _init_communications(self):
        super()._init_communications()
        self.sub_ego_commands = get_subscriber.ego_commands(self._callback_ego_commands)

    def _send_cmd_helper(self, symbol, modifier=()):
        logdebug(f"c2c -> ego: {symbol} - {modifier}")
        try:
            response = self.clt_command_concept(self.node_type, symbol, str(modifier))
            res = response.result
            logdebug("Response for %s: %s" % (symbol, res))
            if res[:4] == "busy":
                raise ReceivedBusy
            elif res[:5] == "abort":
                raise ReceivedAbort
            elif res[:5] == "error":
                logerr(f"Concept ({symbol}) was executed with {res}")
            return res
        except ServiceException as e:
            logerr("Service call failed: %s" % e)
            self.flag_terminate_thread = True
            return str(e)

    def send_cmd(self, symbol: str, modifier=()):
        while 1:
            if self.flag_terminate_thread:
                raise ReceivedAbort
            try:
                return self._send_cmd_helper(symbol, modifier)
            except ReceivedBusy:
                loginfo("send_cmd got Busy")
                sleep(1)  # wait and retry

    def wait(self, timeout: float):
        logdebug("wait")
        start = time()
        while time() < start + timeout:
            if self.flag_terminate_thread:
                raise ReceivedAbort
            if self.flag_pause:
                self._handler_pause()
            sleep(self.WAIT_DESCRETE_SEC)

    def start(self):
        super().start()
        set_param("FLAG_EGO_READY", True)
        self._start_main()
        spin()

    def main(self):
        raise NotImplementedError
