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
from twisteddicom.dimsemessages import Priority
from twisted.python import log
from twisted.internet import reactor, defer
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ClientEndpoint

class StoreSCU(dimse.DIMSEProtocol):
    def __init__(self, datasets, callback, progress_callback, priority = Priority.LOW, move_originator_application_entity_title = None, move_originator_message_id = None):
        super(StoreSCU, self).__init__(supported_abstract_syntaxes = list(set(ds.SOPClassUID for ds in datasets)),
                                       supported_transfer_syntaxes = list(set(ds.file_meta.TransferSyntaxUID for ds in datasets)))
        self.datasets = datasets
        self.callback = callback
        self.progress_callback = progress_callback
        self.status = None
        self.move_originator_message_id = move_originator_message_id
        self.move_originator_application_entity_title = move_originator_application_entity_title
        self.priority = priority
        self.next_message_id = 1
    
    def A_ASSOCIATE_confirmation_accept_indicated(self, a_associate_ac):
        super(StoreSCU, self).A_ASSOCIATE_confirmation_accept_indicated(a_associate_ac)
        log.msg("indicate_A_ASSOCIATE_confirmation_accept")
        log.msg("responding with C-STORE-RQ.")
        self.store_one()

    def store_one(self):
        if len(self.datasets) == 0:
            log.msg("requesting release")
            self.A_RELEASE_request_received()
        else:
            log.msg("storing one more dataset...")
            ds = self.datasets.pop()
            rq = dimsemessages.C_STORE_RQ(affected_sop_class_uid = ds.SOPClassUID,
                                          affected_sop_instance_uid = ds.SOPInstanceUID, 
                                          move_originator_application_entity_title = self.move_originator_application_entity_title,
                                          move_originator_message_id = self.move_originator_message_id,
                                          priority = self.priority,
                                          message_id = self.next_message_id)
            self.next_message_id += 1
            self.send_DIMSE_command(1, rq, ds)

    def C_STORE_RSP_received(self, presentation_context_id, dimse_command, dimse_data):
        log.msg("C_STORE_RSP: status %s" % dimse_command.status)
        self.status = dimse_command.status
        self.store_one()
        if self.progress_callback != None:
            self.progress_callback(dimse_command)

    def conn_closed_received(self):
        super(StoreSCU, self).conn_closed_received()
        self.callback(self.status)

class StoreSCUFactory(Factory, object):
    def __init__(self, calling_ae_title, called_ae_title, datasets, callback, progress_callback,
                 priority = Priority.LOW, 
                 move_originator_message_id = None, 
                 move_originator_application_entity_title = None):
        super(StoreSCUFactory, self).__init__()
        self.called_ae_title = called_ae_title
        self.calling_ae_title = calling_ae_title
        self.datasets = datasets
        self.priority = priority
        self.move_originator_application_entity_title = move_originator_application_entity_title
        self.move_originator_message_id = move_originator_message_id
        self.callback = callback
        self.progress_callback = progress_callback
    def buildProtocol(self, addr):
        protocol = StoreSCU(datasets = self.datasets, 
                            priority = self.priority, 
                            move_originator_message_id = self.move_originator_message_id, 
                            move_originator_application_entity_title = self.move_originator_application_entity_title, 
                            callback = self.callback,
                            progress_callback = self.progress_callback)
        protocol.calling_ae_title = self.calling_ae_title
        protocol.called_ae_title = self.called_ae_title
        protocol.A_ASSOCIATE_request_received()
        return protocol

def store(datasets, host, port, calling_ae_title, called_ae_title, priority = Priority.LOW, move_originator_application_entity_title = None, move_originator_message_id = None, progress_callback = None):
    d = defer.Deferred()
    point = TCP4ClientEndpoint(reactor, host = host, port = port, timeout=5)
    point.connect(StoreSCUFactory(calling_ae_title = calling_ae_title, called_ae_title = called_ae_title, 
                                  datasets = datasets, callback = d.callback, progress_callback = progress_callback,
                                  priority = priority, 
                                  move_originator_message_id = move_originator_message_id, 
                                  move_originator_application_entity_title = move_originator_application_entity_title))
    return d

if __name__== '__main__':
    import sys
    log.startLogging(sys.stdout)
    if len(sys.argv) < 6:
        log.msg("Syntax: %s <host> <port> <calling_ae_title> <called_ae_title> <filename> [<filename> ...]" % (sys.argv[0],))
        sys.exit(1)
    datasets = [dicom.read_file(fn, force=True) for fn in sys.argv[5:]]
    d = store(datasets = datasets, host = sys.argv[1], port = int(sys.argv[2]), calling_ae_title = sys.argv[3], called_ae_title = sys.argv[4])
    d.addCallback(lambda x: reactor.stop())
    reactor.run()
