"""
Test cases for twisteddicom.sockhandler
"""

import struct

from twisteddicom import sockhandler, pdu, upper_layer, dimsemessages
from twisteddicom.utils import get_uid
import twisteddicom.test.test_factory as tf

from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import protocol, error, task


class DICOMUpperLayerServiceTester(upper_layer.DICOMUpperLayerServiceProvider):
    def __init__(self, is_association_requestor):
        upper_layer.DICOMUpperLayerServiceProvider.__init__(self, is_association_requestor,
                                                            supported_abstract_syntaxes = [get_uid("RT Plan Storage")])
        self._called_methods = []
        self.transport = proto_helpers.StringTransport()
        self.called_ae_title = "hej"
        self.calling_ae_title = "bla"
        self.presentation_contexts_requested = self.get_presentation_contexts()
        self.presentation_contexts_accepted = self.validate_presentation_contexts(pdu.A_ASSOCIATE_RQ(presentation_context_items = self.get_presentation_contexts()))
        self.user_information_item_accepted = pdu.UserInformationItem(self.get_application_association_information())

    def validate_presentation_contexts(self, a_associate_rq):
        pcis = []
        for pci in a_associate_rq.presentation_context_items:
            pcis.append(pdu.A_ASSOCIATE_AC.PresentationContextItem(presentation_context_id = pci.presentation_context_id,
                                                                   result_reason = 0,
                                                                   transfer_syntax = pci.transfer_syntaxes[0]))
        return pcis

    def start_ARTIM(self):
        self._called_methods.append("start_ARTIM")

    def stop_ARTIM(self):
        self._called_methods.append("stop_ARTIM")

    def A_RELEASE_confirmation_indicated(self):
        self._called_methods.append("A_RELEASE_confirmation_indicated")

    def P_DATA_indicated(self, data):
        self._called_methods.append("P_DATA_indicated")

    def A_ABORT_confirmation_indicated(self, reason_diag, source):
        self._called_methods.append("A_ABORT_confirmation_indicated")

    def A_ASSOCIATE_confirmation_accept_indicated(self, a_associate_ac):
        self._called_methods.append("A_ASSOCIATE_confirmation_accept_indicated")
        
    def A_ASSOCIATE_confirmation_reject_indicated(self):
        self._called_methods.append("A_ASSOCIATE_confirmation_reject_indicated")

    def A_ASSOCIATE_indicated(self, a_associate_rq):
        self._called_methods.append("A_ASSOCIATE_indicated")

    def A_RELEASE_indicated(self, a_release_rq):
        self._called_methods.append("A_RELEASE_indicated")

    def A_RELEASE_release_collision_indicated(self):
        self._called_methods.append("A_RELEASE_release_collision_indicated")

    def Transport_Connection_Response_indicated(self):
        self._called_methods.append("Transport_Connection_Response_indicated")
        
    def A_ASSOCIATE_request_received(self):
        self._called_methods.append("A_ASSOCIATE_request_received")

    def Transport_Connection_Confirmation_received(self):
        self._called_methods.append("Transport_Connection_Confirmation_received")

    def Transport_Connection_Indication_received(self):
        self._called_methods.append("Transport_Connection_Indication_received")

    def A_ASSOCIATE_AC_PDU_received(self, data):
        self._called_methods.append("A_ASSOCIATE_AC_PDU_received")

    def A_ASSOCIATE_RJ_PDU_received(self, data):
        self._called_methods.append("A_ASSOCIATE_RJ_PDU_received")

    def A_ASSOCIATE_RQ_PDU_received(self, data):
        self._called_methods.append("A_ASSOCIATE_RQ_PDU_received")

    def A_ASSOCIATE_response_accept_received(self):
        self._called_methods.append("A_ASSOCIATE_response_accept_received")

    def A_ASSOCIATE_response_reject_received(self):
        self._called_methods.append("A_ASSOCIATE_response_reject_received")

    def P_DATA_request_received(self, data_values):
        self._called_methods.append("P_DATA_request_received")

    def P_DATA_TF_PDU_received(self, data):
        self._called_methods.append("P_DATA_TF_PDU_received")

    def A_RELEASE_request_received(self):
        self._called_methods.append("A_RELEASE_request_received")

    def A_RELEASE_RQ_PDU_received(self, data):
        self._called_methods.append("A_RELEASE_RQ_PDU_received")

    def A_RELEASE_RP_PDU_received(self, data):
        self._called_methods.append("A_RELEASE_RP_PDU_received")

    def A_RELEASE_response_received(self, data):
        self._called_methods.append("A_RELEASE_response_received")

    def A_ABORT_request_received(self, data):
        self._called_methods.append("A_ABORT_request_received")

    def A_ABORT_PDU_received(self, data):
        self._called_methods.append("A_ABORT_PDU_received")

    def conn_closed_received(self):
        self._called_methods.append("conn_closed_received")

    def ARTIM_expired(self):
        self._called_methods.append("ARTIM_expired")

    def unrecognized_or_invalid_PDU_received(self, data):
        self._called_methods.append("unrecognized_or_invalid_PDU_received")



class DICOMUpperLayerServiceStateMachineTester(upper_layer.DICOMUpperLayerServiceProvider):
    def __init__(self, is_association_requestor):
        super(DICOMUpperLayerServiceStateMachineTester, self).__init__(is_association_requestor)
        self._called_methods = []

    def do_AE_1(self):
        """Issue TRANSPORT CONNECT request primitive to local transport service."""
        self._called_methods.append("do_AE_1")

    def do_AE_2(self):
        """Send A-ASSOCIATE-RQ-PDU."""
        self._called_methods.append("do_AE_2")

    def do_AE_3(self, a_associate_ac):
        """Issue A-ASSOCIATE confirmation (accept) primitive."""
        self._called_methods.append("do_AE_3")

    def do_AE_4(self):
        """Issue A-ASSOCIATE confirmation (reject) primitive and close transport connection."""
        self._called_methods.append("do_AE_4")

    def do_AE_5(self):
        """Issue Transport connection response primitive; start ARTIM timer."""
        self._called_methods.append("do_AE_5")

    def do_AE_6(self, a_associate_rq, is_acceptable):
        """Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service-provider:
               issue A-ASSOCIATE indication primitive.
           otherwise: 
               issue A-ASSOCIATE-RJ-PDU and start ARTIM timer."""
        self._called_methods.append("do_AE_6")

    def do_AE_7(self):
        """Send A-ASSOCIATE-AC PDU."""
        self._called_methods.append("do_AE_7")

    def do_AE_8(self):
        """Send A-ASSOCIATE-RJ PDU and start ARTIM timer """
        self._called_methods.append("do_AE_8")

    def do_DT_1(self, data_values):
        """Send P-DATA-TF PDU."""
        self._called_methods.append("do_DT_1")

    def do_DT_2(self, data):
        """Send P-DATA indication primitive."""
        self._called_methods.append("do_DT_2")

    def do_AR_1(self):
        """Send A-RELEASE-RQ PDU."""
        self._called_methods.append("do_AR_1")

    def do_AR_2(self, a_release_rq):
        """Issue A-RELEASE indication primitive."""
        self._called_methods.append("do_AR_2")

    def do_AR_3(self):
        """Issue A-RELEASE confirmation primitive, and close transport connection."""
        self._called_methods.append("do_AR_3")

    def do_AR_4(self):
        """Issue A-RELEASE-RP PDU and start ARTIM timer."""
        self._called_methods.append("do_AR_4")

    def do_AR_5(self):
        """Stop ARTIM timer."""
        self._called_methods.append("do_AR_5")

    def do_AR_6(self, data):
        """Issue P-DATA indication."""
        self._called_methods.append("do_AR_6")

    def do_AR_7(self, data_values):
        """Issue P-DATA-TF PDU."""
        self._called_methods.append("do_AR_7")

    def do_AR_8(self):
        """Issue A-RELEASE indication (release collision)"""
        self._called_methods.append("do_AR_8")

    def do_AR_9(self):
        """Send A-RELEASE-RP PDU."""
        self._called_methods.append("do_AR_9")

    def do_AR_10(self):
        """Issue A-RELEASE confirmation primitive """
        self._called_methods.append("do_AR_10")

    def do_AA_1(self, reason_diag, source):
        """Send A-ABORT PDU (service-user source) and start (or restart if already started) ARTIM timer;."""
        self._called_methods.append("do_AA_1")

    def do_AA_2(self):
        """Stop ARTIM timer if running. Close transport connection."""
        self._called_methods.append("do_AA_2")

    def do_AA_3(self, reason_diag, source):
        """If (service-user inititated abort)
               issue A-ABORT indication and close transport connection.
           otherwise (service-provider inititated abort):
               issue A-P-ABORT indication and close transport connection."""
        self._called_methods.append("do_AA_3")

    def do_AA_4(self, reason_diag):
        """Issue A-P-ABORT indication primitive."""
        self._called_methods.append("do_AA_4")

    def do_AA_5(self):
        """Stop ARTIM timer."""
        self._called_methods.append("do_AA_5")

    def do_AA_6(self):
        """Ignore PDU."""
        self._called_methods.append("do_AA_6")

    def do_AA_7(self):
        """Send A-ABORT PDU."""
        self._called_methods.append("do_AA_7")

    def do_AA_8(self):
        """Send A-ABORT PDU (service-provider source), issue an A-P-ABORT indication, and start ARTIM timer."""
        self._called_methods.append("do_AA_8")



# Table 9-10 in PS3.8

state_transitions = {
#           Sta1             Sta2             Sta3             Sta4            Sta5            Sta6            Sta7            Sta8            Sta9            Sta10            Sta11            Sta12            Sta13
    'A-ASSOCIATE Request (local user)':
        {1:('AE-1',  4),                                                                                                                                                                                                   },
    'Transport Conn. Confirm (local transport service)':
        {                                                4:('AE-2',  5),                                                                                                                                                   },
    'A-ASSOCIATE-AC PDU (received on transport connection)':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AE-3',  6), 6:('AA-8', 13), 7:('AA-8', 13), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-6', 13)},
    'A-ASSOCIATE-RJ PDU (received on transport connection)':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AE-4',  1), 6:('AA-8', 13), 7:('AA-8', 13), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-6', 13)},
    'Transport Connection Indication (local transport service)':
        {1:('AE-5',  2),                                                                                                                                                                                                   },
    'A-ASSOCIATE-RQ PDU (received on transport connection)':
        {                2:('AE-6', -1), 3:('AA-8', 13),                 5:('AA-8', 13), 6:('AA-8', 13), 7:('AA-8', 13), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-7', 13)},
    'A-ASSOCIATE response primitive (accept)':
        {                                3:('AE-7',  6),                                                                                                                                                                   },
    'A-ASSOCIATE response primitive (reject)':
        {                                3:('AE-8', 13),                                                                                                                                                                   },
    'P-DATA request primitive ':
        {                                                                                6:('DT-1',  6),                 8:('AR-7',  8),                                                                                   },
    'P-DATA-TF PDU':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AA-8', 13), 6:('DT-2',  6), 7:('AR-6',  7), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-6', 13)},
    'A-RELEASE Request primitive':
        {                                                                                6:('AR-1',  7),                                                                                                                   },
    'A-RELEASE-RQ PDU (received on open transport connection)':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AA-8', 13), 6:('AR-2',  8), 7:('AR-8', -2), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-6', 13)},
    'A-RELEASE-RP PDU (received on transport connection)':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AA-8', 13), 6:('AA-8', 13), 7:('AR-3',  1), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AR-10',12), 11:('AR-3',  1), 12:('AA-8', 13), 13:('AA-6', 13)},
    'A-RELEASE Response primitive':
        {                                                                                                                8:('AR-4', 13), 9:('AR-9', 11),                                   12:('AR-4', 13),                },
    'A-ABORT Request primitive':
        {                                3:('AA-1', 13), 4:('AA-2',  1), 5:('AA-1', 13), 6:('AA-1', 13), 7:('AA-1', 13), 8:('AA-1', 13), 9:('AA-1', 13), 10:('AA-1', 13), 11:('AA-1', 13), 12:('AA-1', 13),                },
    'A-ABORT PDU (received on open transport connection)':
        {                2:('AA-2',  1), 3:('AA-3',  1),                 5:('AA-3',  1), 6:('AA-3',  1), 7:('AA-3',  1), 8:('AA-3',  1), 9:('AA-3',  1), 10:('AA-3',  1), 11:('AA-3',  1), 12:('AA-3',  1), 13:('AA-2',  1)},
    'Transport connection closed indication (local transport service)':
        {                2:('AA-5',  1), 3:('AA-4',  1), 4:('AA-4',  1), 5:('AA-4',  1), 6:('AA-4',  1), 7:('AA-4',  1), 8:('AA-4',  1), 9:('AA-4',  1), 10:('AA-4',  1), 11:('AA-4',  1), 12:('AA-4',  1), 13:('AR-5',  1)},
    'ARTIM timer expired (Association reject/release timer)':
        {                2:('AA-2',  1),                                                                                                                                                                    13:('AA-2',  1)},
    'Unrecognized or invalid PDU received':
        {                2:('AA-1', 13), 3:('AA-8', 13),                 5:('AA-8', 13), 6:('AA-8', 13), 7:('AA-8', 13), 8:('AA-8', 13), 9:('AA-8', 13), 10:('AA-8', 13), 11:('AA-8', 13), 12:('AA-8', 13), 13:('AA-7', 13)},
    }


indication_methods = {
    'A-ASSOCIATE Request (local user)': 
        lambda x: x.A_ASSOCIATE_request_received(),
    'Transport Conn. Confirm (local transport service)': 
        lambda x: x.Transport_Connection_Confirmation_received(),
    'A-ASSOCIATE-AC PDU (received on transport connection)': 
        lambda x: x.A_ASSOCIATE_AC_PDU_received(None),
    'A-ASSOCIATE-RJ PDU (received on transport connection)': 
        lambda x: x.A_ASSOCIATE_RJ_PDU_received(None),
    'Transport Connection Indication (local transport service)': 
        lambda x: x.Transport_Connection_Indication_received(),
    'A-ASSOCIATE-RQ PDU (received on transport connection)': 
        lambda x: x.A_ASSOCIATE_RQ_PDU_received(tf.test_factories[pdu.A_ASSOCIATE_RQ]()),
    'A-ASSOCIATE response primitive (accept)': 
        lambda x: x.A_ASSOCIATE_response_accept_received(),
    'A-ASSOCIATE response primitive (reject)': 
        lambda x: x.A_ASSOCIATE_response_reject_received(),
    'P-DATA request primitive ': 
        lambda x: x.P_DATA_request_received("testdata"),
    'P-DATA-TF PDU': 
        lambda x: x.P_DATA_TF_PDU_received(tf.test_factories[pdu.P_DATA_TF]()),
    'A-RELEASE Request primitive': 
        lambda x: x.A_RELEASE_request_received(),
    'A-RELEASE-RQ PDU (received on open transport connection)': 
        lambda x: x.A_RELEASE_RQ_PDU_received(tf.test_factories[pdu.A_ASSOCIATE_RQ]()),
    'A-RELEASE-RP PDU (received on transport connection)': 
        lambda x: x.A_RELEASE_RP_PDU_received(None),
    'A-RELEASE Response primitive': 
        lambda x: x.A_RELEASE_response_received(None),
    'A-ABORT Request primitive': 
        lambda x: x.A_ABORT_request_received(None),
    'A-ABORT PDU (received on open transport connection)': 
        lambda x: x.A_ABORT_PDU_received(tf.test_factories[pdu.A_ABORT]()),
    'Transport connection closed indication (local transport service)': 
        lambda x: x.conn_closed_received(),
    'ARTIM timer expired (Association reject/release timer)': 
        lambda x: x.ARTIM_expired(),
    'Unrecognized or invalid PDU received': 
        lambda x: x.unrecognized_or_invalid_PDU_received(None),
    }

states = range(1,14)

actions = ['AE-1', 'AE-2', 'AE-3', 'AE-4', 'AE-5', 'AE-6', 'AE-7', 'AE-8', 
           'DT-1', 'DT-2', 
           'AR-1', 'AR-2', 'AR-3', 'AR-4', 'AR-5', 'AR-6', 'AR-7', 'AR-8', 'AR-9', 'AR-10', 
           'AA-1', 'AA-2', 'AA-3', 'AA-4', 'AA-5', 'AA-6', 'AA-7', 'AA-8']

action_methods = [
    ('AE_1', lambda x: x.do_AE_1(), ['Transport_Connection_Indication_received'], []),
    ('AE_2', lambda x: x.do_AE_2(), [], [pdu.A_ASSOCIATE_RQ]),
    ('AE_3', lambda x: x.do_AE_3(tf.test_factories[pdu.A_ASSOCIATE_RQ]()), ['A_ASSOCIATE_confirmation_accept_indicated'], []),
    ('AE_4', lambda x: x.do_AE_4(), ['A_ASSOCIATE_confirmation_reject_indicated'], []),
    ('AE_5', lambda x: x.do_AE_5(), ['Transport_Connection_Response_indicated', 'start_ARTIM'], []),
    ('AE_6', lambda x: x.do_AE_6(tf.test_factories[pdu.A_ASSOCIATE_RQ](), True), ['stop_ARTIM', 'A_ASSOCIATE_indicated'], []),
    ('AE_6', lambda x: x.do_AE_6(tf.test_factories[pdu.A_ASSOCIATE_RQ](), False), ['stop_ARTIM', 'start_ARTIM'], [pdu.A_ASSOCIATE_RJ]),
    ('AE_7', lambda x: x.do_AE_7(), [], [pdu.A_ASSOCIATE_AC]),
    ('AE_8', lambda x: x.do_AE_8(), ['start_ARTIM'], [pdu.A_ASSOCIATE_RJ]),
    ('DT_1', lambda x: x.do_DT_1(((0, "HEJ"),)), [], [pdu.P_DATA_TF]),
    ('DT_2', lambda x: x.do_DT_2("blabla"), ['P_DATA_indicated'], []),
    ('AR_1', lambda x: x.do_AR_1(), [], [pdu.A_RELEASE_RQ]),
    ('AR_2', lambda x: x.do_AR_2(tf.test_factories[pdu.A_ASSOCIATE_RQ]()), ['A_RELEASE_indicated'], []),
    ('AR_3', lambda x: x.do_AR_3(), ['A_RELEASE_confirmation_indicated'], []),
    ('AR_4', lambda x: x.do_AR_4(), ['start_ARTIM'], [pdu.A_RELEASE_RP]),
    ('AR_5', lambda x: x.do_AR_5(), ['stop_ARTIM'], []),
    ('AR_6', lambda x: x.do_AR_6("blabla"), ['P_DATA_indicated'], []),
    ('AR_7', lambda x: x.do_AR_7(((0, "HEJ"),)), [], [pdu.P_DATA_TF]),
    ('AR_8', lambda x: x.do_AR_8(), ['A_RELEASE_release_collision_indicated'], []),
    ('AR_9', lambda x: x.do_AR_9(), [], [pdu.A_RELEASE_RP]),
    ('AR_10', lambda x: x.do_AR_10(), ['A_RELEASE_confirmation_indicated'], []),
    ('AA_1', lambda x: x.do_AA_1(1, 2), ['start_ARTIM'], [pdu.A_ABORT]),
    ('AA_2', lambda x: x.do_AA_2(), ['stop_ARTIM'], []),
    ('AA_3', lambda x: x.do_AA_3(2, 0), ['A_ABORT_confirmation_indicated'], []),
    ('AA_3', lambda x: x.do_AA_3(2, 2), ['A_ABORT_confirmation_indicated'], []),
    ('AA_4', lambda x: x.do_AA_4(2), ['A_ABORT_confirmation_indicated'], []),
    ('AA_5', lambda x: x.do_AA_5(), ['stop_ARTIM'], []),
    ('AA_6', lambda x: x.do_AA_6(), [], []),
    ('AA_7', lambda x: x.do_AA_7(), [], [pdu.A_ABORT]),
    ('AA_8', lambda x: x.do_AA_8(), ['A_ABORT_confirmation_indicated', 'start_ARTIM'], [pdu.A_ABORT]),
]

class DICOMUpperLayerServiceProviderTestCase(unittest.SynchronousTestCase):
    def test_state_machine(self):
        """
        Test buffering for different packet size, checking received matches
        expected data.
        """
        for event in indication_methods:
            for state in states:
                if not state_transitions[event].has_key(state):
                    continue
                #print "%s - %s" % (event, state)
                uls = DICOMUpperLayerServiceStateMachineTester(False)
                uls.state = state
                uls.is_acceptable = lambda x: 3
                indication_methods[event](uls)
                self.assertEqual(1, len(uls._called_methods))
                self.assertEqual("do_" + state_transitions[event][state][0].replace("-", "_"), uls._called_methods[0])
                if state_transitions[event][state][1] > 0:
                    self.assertEqual(state_transitions[event][state][1], uls.state)
                elif state_transitions[event][state][1] == -1:
                    self.assertEqual(uls.state, 3)
                elif state_transitions[event][state][1] == -2:
                    if uls.is_association_requestor:
                        self.assertEqual(uls.state, 9)
                    else:
                        self.assertEqual(uls.state, 10)

    def test_actions(self):
        for action, call, methods, messages in action_methods:
            #print "action:", action
            uls = DICOMUpperLayerServiceTester(False)
            uls.makeConnection(uls.transport)
            call(uls)
            buf = uls.transport.value()
            if len(messages) == 1:
                pdu_type, = struct.unpack("B", buf[0])
                self.assertEqual(pdu.pdus[pdu_type], messages[0])
            self.assertEqual(set(uls._called_methods), set(['Transport_Connection_Indication_received'] + methods))
        

