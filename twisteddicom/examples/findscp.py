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
from twisteddicom.utils import get_uid, match_dataset
from twisted.python import log
import os
import glob

class FindSCP(dimse.DIMSEProtocol):
    def __init__(self, folder):
        super(FindSCP, self).__init__(supported_abstract_syntaxes = [
                                        get_uid("Patient Root Query/Retrieve Information Model - FIND"),
                                        get_uid("Study Root Query/Retrieve Information Model - FIND"),
                                        get_uid("Patient/Study Only Query/Retrieve Information Model  - FIND"),
                                        get_uid("Modality Worklist Information Model - FIND"),
                                        get_uid("Verification SOP Class"),
                                      ])
        self.folder = folder

    def C_ECHO_RQ_received(self, presentation_context_id, echo_rq, dimse_data):
        log.msg("received DIMSE command %s on presentation context %i" % (echo_rq, presentation_context_id))
        assert echo_rq.__class__ == dimsemessages.C_ECHO_RQ
        log.msg("replying")
        self.send_DIMSE_command(presentation_context_id, dimsemessages.C_ECHO_RSP(echo_rq.message_id))

    def C_FIND_RQ_received(self, presentation_context_id, find_rq, query):
        log.msg("received %s on presentation context %i" % (find_rq, presentation_context_id))

        log.msg("%s" % query)

        for f in glob.glob(os.path.join(self.folder, "*.dcm*")):
            try:
                ds = dicom.read_file(f)
            except dicom.filereader.InvalidDicomError, e:
                log.err(e)
                continue
            
            is_match, result_ds = match_dataset(query, ds)
            if not is_match:
                continue
            self.send_DIMSE_command(presentation_context_id,
                                    dimsemessages.C_FIND_RSP(status = 0xff00,
                                                             message_id_being_responded_to = find_rq.message_id,
                                                             affected_sop_class_uid = find_rq.affected_sop_class_uid,
                                                             data_set_present = True),
                                    result_ds)
            


        self.send_DIMSE_command(presentation_context_id, 
                                dimsemessages.C_FIND_RSP(status = 0, 
                                                         message_id_being_responded_to = find_rq.message_id,
                                                         affected_sop_class_uid = find_rq.affected_sop_class_uid))

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint

class FindSCPFactory(Factory, object):
    def __init__(self, folder):
        super(FindSCPFactory, self).__init__()
        self.folder = folder
    def buildProtocol(self, addr):
        protocol = FindSCP(folder = self.folder)
        return protocol

def gotProtocol(p):
    log.msg("hej")
    pass
        
if __name__== '__main__':
    import sys
    log.startLogging(sys.stdout)
    if len(sys.argv) != 3:
        log.msg("Syntax: %s <port> <folder>" % sys.argv[0])
        sys.exit(1)
    endpoint = TCP4ServerEndpoint(reactor, port = int(sys.argv[1]))
    endpoint.listen(FindSCPFactory(folder = sys.argv[2]))
    reactor.run()
    log.msg("reactor.run() exited")
