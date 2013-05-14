"""
Test cases for twisteddicom.sockhandler
"""

import inspect
from twisteddicom import dimsemessages

def tf_DIMSE(dimsecls):
    args = {
        'action_type_id': 18,
        'affected_sop_class_uid': "1.2.3",
        'affected_sop_instance_uid': "1.2.4",
        'data_set_present': [False, True],
        'event_type_id': 19,
        'message_id': 20,
        'message_id_being_responded_to': 21,
        'move_destination': "movedest",
        'move_originator_application_entity_title': "moveorigapp",
        'move_originator_message_id': 27,
        'number_of_completed_sub_operations': 22,
        'number_of_failed_sub_operations': 23,
        'number_of_remaining_sub_operations': 24,
        'number_of_warning_sub_operations': 25,
        'priority': [dimsemessages.Priority.LOW, dimsemessages.Priority.MEDIUM, dimsemessages.Priority.HIGH],
        'requested_sop_class_uid': "1.2.5",
        'requested_sop_instance_uid': "1.2.6",
        'status': 26,
    }
    initargs = inspect.getargspec(dimsecls.__init__).args
    initargs.remove('self')
    res = [{}]
    def dictadd(a, b):
        a2 = dict(a)
        a2.update(b)
        return a2
    for arg in initargs:
        if isinstance(args[arg], list):
            res = [dictadd(r, {arg: argvar}) for r in res for argvar in args[arg]]
        else:
            res = [dictadd(r, {arg: args[arg]}) for r in res]

    return [dimsecls(**{k:v for k,v in r.iteritems()}) for r in res]

import sys
sys.path.append("../..")

from twisteddicom import sockhandler, pdu
import test_factory
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import protocol, error, task

from twisteddicom.dimsemessages import C_STORE_RQ, C_STORE_RSP, C_GET_RQ, C_GET_RSP
from twisteddicom.dimsemessages import C_FIND_RQ, C_FIND_RSP, C_MOVE_RQ, C_MOVE_RSP, C_ECHO_RQ, C_ECHO_RSP
from twisteddicom.dimsemessages import N_EVENT_REPORT_RQ, N_EVENT_REPORT_RSP, N_GET_RQ, N_GET_RSP
from twisteddicom.dimsemessages import N_SET_RQ, N_SET_RSP, N_ACTION_RQ, N_ACTION_RSP
from twisteddicom.dimsemessages import N_DELETE_RQ, N_DELETE_RSP, N_CREATE_RQ, N_CREATE_RSP, C_CANCEL_RQ
from twisteddicom.dimsemessages import unpack_dataset, commands

class DIMSEMessagesTestCase(unittest.SynchronousTestCase):
    def test_roundtrip(self):
        """
        """
        
        for cls in [C_STORE_RQ, C_STORE_RSP, C_GET_RQ, C_GET_RSP, 
                    C_FIND_RQ, C_FIND_RSP, C_MOVE_RQ, C_MOVE_RSP, C_ECHO_RQ, C_ECHO_RSP, 
                    N_EVENT_REPORT_RQ, N_EVENT_REPORT_RSP, N_GET_RQ, N_GET_RSP, 
                    N_SET_RQ, N_SET_RSP, N_ACTION_RQ, N_ACTION_RSP, 
                    N_DELETE_RQ, N_DELETE_RSP, N_CREATE_RQ, N_CREATE_RSP, C_CANCEL_RQ]:
            for obj in tf_DIMSE(cls):
                p = obj.pack()
                rp = cls()
                pd = unpack_dataset(p)
                rp.unpack(pd)
                prp = rp.pack()
                self.assertEqual(pd.CommandField, commands[cls])
                self.assertEqual(obj.__dict__, rp.__dict__)
                self.assertEqual(p, prp)

