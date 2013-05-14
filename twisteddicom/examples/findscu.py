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

import dicom
from twisteddicom import dimse, dimsemessages
from twisteddicom.utils import get_uid
from twisted.python import log

class FindSCU(dimse.DIMSEProtocol):
    def __init__(self, tags):
        super(FindSCU, self).__init__(is_association_requestor = True, 
                                      supported_abstract_syntaxes = [get_uid("Patient Root Query/Retrieve Information Model - FIND")])
        self.query = dicom.dataset.Dataset()
        for key, value in tags.iteritems():
            setattr(self.query, key, value)
    
    def A_ASSOCIATE_confirmation_accept_indicated(self, a_associate_ac):
        super(FindSCU, self).A_ASSOCIATE_confirmation_accept_indicated(a_associate_ac)
        log.msg("indicate_A_ASSOCIATE_confirmation_accept")
        log.msg("responding with C-FIND-RQ %s." % self.query)
        rq = dimsemessages.C_FIND_RQ(affected_sop_class_uid = get_uid("Patient Root Query/Retrieve Information Model - FIND"),
                                      message_id = 1)
        self.send_DIMSE_command(1, rq, self.query)

    def C_FIND_RSP_received(self, presentation_context_id, dimse_command, dimse_data):
        log.msg("C_FIND_RSP: status %04x" % dimse_command.status)
        log.msg("C_FIND_RSP: data: %s" % dimse_data)
        log.msg("requesting release")
        if dimse_command.status != 0xFF01:
            self.A_RELEASE_request_received()

    def A_RELEASE_confirmation_indicated(self):
        log.msg("Disconnected.")
        reactor.stop()


from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ClientEndpoint

class FindSCUFactory(Factory, object):
    def __init__(self, calling_ae_title, called_ae_title, tags):
        super(FindSCUFactory, self).__init__()
        self.called_ae_title = called_ae_title
        self.calling_ae_title = calling_ae_title
        self.tags = tags
    def buildProtocol(self, addr):
        protocol = FindSCU(dict([t.split("=",1) for t in self.tags]))
        protocol.calling_ae_title = self.calling_ae_title
        protocol.called_ae_title = self.called_ae_title
        protocol.A_ASSOCIATE_request_received()
        return protocol

if __name__== '__main__':
    import sys
    log.startLogging(sys.stdout)
    if len(sys.argv) <= 5:
        log.msg("Syntax: %s <host> <port> <calling_ae_title> <called_ae_title> { <tag=value> ... }", sys.argv[0])
        sys.exit(1)
    point = TCP4ClientEndpoint(reactor, host = sys.argv[1], port = int(sys.argv[2]), timeout=5)
    d = point.connect(FindSCUFactory(calling_ae_title = sys.argv[3], called_ae_title = sys.argv[4], tags=sys.argv[5:]))
    reactor.run()
