"""
Test cases for twisteddicom.sockhandler
"""

from twisteddicom import sockhandler, pdu
import test_factory
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import protocol, error, task

class DICOMUpperLayerServiceReceiverTestCase(unittest.SynchronousTestCase):
    def test_simple_packet(self):
        """
        Test buffering for different packet size, checking received matches
        expected data.
        """
        
        for tf in test_factory.test_factories.itervalues():
            test_pdu = tf()
            pdu_data = test_pdu.pack()
            unpacked_pdu = tf()
            unpacked_pdu.unpack(pdu_data)
            repacked_pdu_data = unpacked_pdu.pack()
            self.assertEqual(pdu_data, repacked_pdu_data)

