"""
Test cases for twisteddicom.sockhandler
"""


from twisteddicom import sockhandler, pdu
import test_factory
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import protocol, error, task

class DICOMUpperLayerServiceTester(sockhandler.DICOMUpperLayerServiceProtocol):
    def __init__(self):
        super(DICOMUpperLayerServiceTester, self).__init__()
        self.received = []
    def pdu_received(self, data):
        self.received.append(data)


class DICOMUpperLayerServiceProtocolTestCase(unittest.SynchronousTestCase):
    def test_simple_packet(self):
        """
        Test buffering for different packet size, checking received matches
        expected data.
        """
        for tf in test_factory.test_factories.itervalues():
            test_pdu = tf()
            pdu_data = test_pdu.pack()
            for packet_size in range(1,len(pdu_data)):
                transport = proto_helpers.StringIOWithoutClosing()
                uls = DICOMUpperLayerServiceTester()
                uls.makeConnection(protocol.FileWrapper(transport))
                for i in range(len(pdu_data) // packet_size + 1):
                    s = pdu_data[i * packet_size:(i + 1) * packet_size]
                    uls.dataReceived(s)
                self.assertEqual(len(uls.received), 1)
                self.assertEqual(uls.received[0].pack(), test_pdu.pack())

