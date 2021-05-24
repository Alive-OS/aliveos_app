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

from .generic_mind_node import GenericMindNode, node_types
from .exceptions import ReceivedAbort, ReceivedBusy
from time import sleep, time

from aliveos_msgs import msg
import rospy
from rospy import ServiceException
from rospy import logdebug, logerr, loginfo, logwarn, ServiceException, set_param


class InstinctNode(GenericMindNode):
    def __init__(self, name, concept_files):
        super().__init__(name=name, concept_files=concept_files, node_type=node_types.INSTINCT_NODE)

    def start(self):
        super().start()
        rospy.spin()

    def _callback_perception_concept(self, perception_concept: msg.PerceptionConcept):
        super()._callback_perception_concept(perception_concept)
        self.callback_perception_concept(perception_concept.symbol, perception_concept.modifier)

    def _send_cmd_helper(self, symbol, modifier=()):
        logdebug(f"c2c -> instinct: {symbol} - {modifier}")
        try:
            response = self.clt_command_concept(self.node_type, symbol, str(modifier))
            res = response.result
            logdebug("Response for %s: %s" % (symbol, res))
            if res[:4] == "busy":
                raise ReceivedBusy
            elif res[:5] == "error":
                logerr(f"Concept ({symbol}) was executed with {res}")
            return res
        except ServiceException as e:
            logerr("Service call failed: %s" % e)
            return str(e)

    def send_cmd(self, symbol: str, modifier=()):
        while 1:
            try:
                return self._send_cmd_helper(symbol, modifier)
            except ReceivedBusy:
                loginfo("send_cmd got Busy")
                sleep(1)  # wait and retry

    def callback_perception_concept(self, symbol, modifier):
        raise NotImplementedError
