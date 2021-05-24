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

import json

from rospkg import RosPack, ResourceNotFound
from rospy import logdebug, logerr, init_node
from rospy.service import ServiceException

from aliveos_msgs import srv, msg
from aliveos_py.ros import get_client, get_subscriber
from aliveos_py.helpers.json_tools import json_to_dict, dict_to_json_str, ValidationError
from . import node_types


class GenericMindNode:
    def __init__(self, name="GenericMindNode", concept_files: list = None, node_type=node_types.GENERIC_NODE):
        self.name = name
        self.node_type = node_type
        self.sensor_cb_thread = None
        self.current_emotion_params = None
        self.current_perception_concept = None
        self.current_perception_concept_mod = None
        # Command concepts
        self.concept_files = concept_files
        # Clients
        self.clt_command_concept = None
        self.clt_command_concept_dsc = None
        self.clt_emotion_core_write = None
        # Subscribers
        self.sub_perception_concept = None
        self.sub_emotion_params = None

        try:
            self.schema_path = RosPack().get_path('aliveos_msgs') + "/json"
        except ResourceNotFound:
            raise ResourceNotFound("Cannot find the aliveos_msgs package")

    def _callback_perception_concept(self, perception_concept: msg.PerceptionConcept):
        logdebug(f"d2c -> mind: {perception_concept.symbol} - {perception_concept.modifier}")
        self.current_perception_concept = perception_concept.symbol
        self.current_perception_concept_mod = perception_concept.modifier

    def _callback_emotion_params(self, params: msg.EmotionParams):
        logdebug(f"ecore -> mind: {params.params_json}")
        params_dict = json.loads(params.params_json)
        self.current_emotion_params = params_dict

    def _init_communications(self):
        self.sub_perception_concept = get_subscriber.perception_concept(self._callback_perception_concept)
        self.sub_emotion_params = get_subscriber.emotion_params(self._callback_emotion_params)
        self.clt_command_concept = get_client.command_concept()
        self.clt_command_concept_dsc = get_client.command_concept_descriptor()
        self.clt_emotion_core_write = get_client.emotion_core_write()

    def _send_command_concept_single(self, cc):
        json_dict = json_to_dict(in_json=cc, in_schema=f"{self.schema_path}/command-concept-dsc.json")
        json_str = dict_to_json_str(in_dict=json_dict)
        m = srv.CommandConceptDescriptorRequest()
        m.descriptor_json = json_str
        self.clt_command_concept_dsc(m)

    def _send_command_concepts(self):
        for cc in self.concept_files:
            try:
                self._send_command_concept_single(cc)
            except ValidationError as e:
                logerr(f"Incorrect input json: {cc}\nError:[{e.message}]")

    def send_cmd(self, symbol: str, modifier=()):
        return self.clt_command_concept(self.node_type, symbol, str(modifier))

    def start(self):
        init_node(self.name, anonymous=False)
        self._init_communications()
        self._send_command_concepts()

    def write_to_emotion_core(self, value: int, change_per_sec: int,
                              param: str) -> srv.EmotionCoreWriteResponse:
        m = srv.EmotionCoreWriteRequest()
        m.value = value
        m.temp_val_per_sec = change_per_sec
        m.temp_param_name = param
        try:
            r = self.clt_emotion_core_write(m)
        except ServiceException:
            logerr("Service PerceptionConceptDescriptor error!")
            r = None
        return r

    def __call__(self):
        self.start()
