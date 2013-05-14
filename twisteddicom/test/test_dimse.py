"""
Test cases for twisteddicom.sockhandler
"""

import struct

from twisteddicom import sockhandler, pdu, upper_layer, dimsemessages, dimse, utils
from twisteddicom.test import test_factory as tf

from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import protocol, error, task

class DIMSETester(dimse.DIMSEProtocol):
    def __init__(self, is_association_requestor):
        super(DIMSETester, self).__init__(is_association_requestor)
        self.transport = proto_helpers.StringTransport()
        self.called_ae_title = "hej"
        self.calling_ae_title = "bla"
        self._sent = []

    def P_DATA_request_received(self, data):
        self._sent.append(data)

class DIMSETestCase(unittest.SynchronousTestCase):
    def test_send(self):
        """
        """
        uls = DIMSETester(False)
        uls.send_DIMSE_command(1, dimsemessages.C_ECHO_RQ())
        self.assertEqual(len(uls._sent), 1)
        self.assertEqual(len(uls._sent[0]), 1)
        self.assertEqual(pdu.PDU.unpack(uls._sent[0][0][1])[1].__class__, pdu.A_ASSOCIATE_RJ)

    def test_recv(self):
        """
        """
        pass
        

