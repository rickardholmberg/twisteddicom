# Copyright (c) 2012 Bo Eric Rickard Holmberg <rickard@holmberg.info>

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from twisted.internet import protocol
from twisted.python import log
from twisted.protocols import basic 

do_log = False

import pdu

class DICOMUpperLayerServiceProtocol(protocol.Protocol, basic._PauseableMixin, object):
    def __init__(self):
        super(DICOMUpperLayerServiceProtocol, self).__init__()
        self._unprocessed = b""

    def Transport_Connection_Response_indicated(self):
        if do_log: log.msg("Transport_Connection_Response_indicated()")

    def A_ABORT_confirmation_indicated(self, reason_diag, source):
        if do_log: log.msg("A_ABORT_confirmation_indicated")
        
    def dataReceived(self, data):
        """
        Receive a stream of data, tokenize it to PDU messages and call pdu_received().
        """
        # Try to minimize string copying (via slices) by keeping one buffer
        # containing all the data we have so far and a separate offset into that
        # buffer.
        # Mimics the state in twisted.protocols.basic. Can be optimized in the case 
        # where short messages are often received. (remember pdu_type, pdu_length etc., 
        # only unpack pdu_type once...)
        if do_log: log.msg("dataReceived(%i)" % len(data))
        all_data = self._unprocessed + data
        current_offset = 0
        
        self._unprocessed = all_data

        while len(all_data) >= (current_offset + 1) and not self.paused:
            current_offset, data = pdu.PDU.unpack(all_data, current_offset)
            if data == None:
                break
            else:
                self.pdu_received(data)

        if current_offset != 0:
            self._unprocessed = all_data[current_offset : ]

    def connectionLost(self, reason):
        self.conn_closed_received()

    def pdu_received(self, data):
        """
        Dispatch PDU messages to the respective *_received handlers.
        """
        if data.__class__ == pdu.A_ASSOCIATE_AC:
            self.A_ASSOCIATE_AC_PDU_received(data)
        elif data.__class__ == pdu.A_ASSOCIATE_RJ:
            self.A_ASSOCIATE_RJ_PDU_received(data)
        elif data.__class__ == pdu.A_ASSOCIATE_RQ:
            self.A_ASSOCIATE_RQ_PDU_received(data)
        elif data.__class__ == pdu.P_DATA_TF:
            self.P_DATA_TF_PDU_received(data)
        elif data.__class__ == pdu.A_RELEASE_RQ:
            self.A_RELEASE_RQ_PDU_received(data)
        elif data.__class__ == pdu.A_RELEASE_RP:
            self.A_RELEASE_RP_PDU_received(data)
        elif data.__class__ == pdu.A_RELEASE_RP:
            self.A_RELEASE_RP_PDU_received(data)
        elif data.__class__ == pdu.A_ABORT:
            self.A_ABORT_PDU_received(data)
        else:
            self.unrecognized_or_invalid_PDU_received(data)

    def A_ASSOCIATE_AC_PDU_received(data):
        pass
    def A_ASSOCIATE_RJ_PDU_received(data):
        pass
    def A_ASSOCIATE_RQ_PDU_received(data):
        pass
    def P_DATA_TF_PDU_received(data):
        pass
    def A_RELEASE_RQ_PDU_received(data):
        pass
    def A_RELEASE_RP_PDU_received(data):
        pass
    def A_RELEASE_RP_PDU_received(data):
        pass
    def A_ABORT_PDU_received(data):
        pass
    def unrecognized_or_invalid_PDU_received(data):
        pass
