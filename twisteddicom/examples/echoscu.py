#!/usr/bin/python
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

from twisteddicom import pdu, dimse, dimsemessages, sockhandler, upper_layer
from twisteddicom.utils import get_uid
from twisted.python import log

sockhandler.do_log = True
pdu.do_log = True
upper_layer.do_log = True
dimse.do_log = True

class EchoSCU(dimse.DIMSEProtocol):
    def __init__(self):
        super(EchoSCU, self).__init__(supported_abstract_syntaxes = [get_uid("Verification SOP Class")])
        self.received_c_echo_rsp = False

    def A_ASSOCIATE_confirmation_accept_indicated(self, a_associate_ac):
        super(EchoSCU, self).A_ASSOCIATE_confirmation_accept_indicated(a_associate_ac)
        log.msg("indicate_A_ASSOCIATE_confirmation_accept")
        log.msg("responding with C-ECHO-RQ.")
        self.send_DIMSE_command(1, dimsemessages.C_ECHO_RQ())

    def C_ECHO_RSP_received(self, presentation_context_id, dimse_command, dimse_data):
        log.msg("received C_ECHO_RSP command %s" % dimse_command)
        self.received_c_echo_rsp = True
        log.msg("requesting release")
        self.A_RELEASE_request_received()

    def conn_closed_received(self):
        super(EchoSCU, self).conn_closed_received()
        reactor.stop()

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

class EchoSCUFactory(Factory, object):
    def __init__(self, calling_ae_title, called_ae_title):
        super(EchoSCUFactory, self).__init__()
        self.called_ae_title = called_ae_title
        self.calling_ae_title = calling_ae_title
    def buildProtocol(self, addr):
        protocol = EchoSCU()
        protocol.calling_ae_title = self.calling_ae_title
        protocol.called_ae_title = self.called_ae_title
        protocol.A_ASSOCIATE_request_received()
        return protocol

if __name__== '__main__':
    import sys
    log.startLogging(sys.stdout)
    if len(sys.argv) != 5:
        log.msg("Syntax: %s <host> <port> <calling_ae_title> <called_ae_title>" % sys.argv[0])
        sys.exit(1)
    point = TCP4ClientEndpoint(reactor, host = sys.argv[1], port = int(sys.argv[2]), timeout=5)
    d = point.connect(EchoSCUFactory(calling_ae_title = sys.argv[3], called_ae_title = sys.argv[4]))
    reactor.run()
