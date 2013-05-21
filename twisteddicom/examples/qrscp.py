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
import storescu
from twisteddicom.utils import get_uid, match_dataset, get_level_identifier
from twisted.python import log
import os
import glob
import json

from twisted.internet import reactor, defer
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint

class QRSCP(dimse.DIMSEProtocol):
    def __init__(self, folder, move_destinations):
        super(QRSCP, self).__init__(is_association_requestor = False, 
                                    supported_abstract_syntaxes = [
                                        get_uid("Patient Root Query/Retrieve Information Model - FIND"),
                                        get_uid("Patient Root Query/Retrieve Information Model - MOVE"),
                                        get_uid("Study Root Query/Retrieve Information Model - FIND"),
                                        get_uid("Study Root Query/Retrieve Information Model - MOVE"),
                                        get_uid("Verification SOP Class")])
        self.folder = folder
        self.move_destinations = move_destinations

    def C_ECHO_RQ_received(self, presentation_context_id, echo_rq, dimse_data):
        log.msg("received DIMSE command %s on presentation context %i" % (echo_rq, presentation_context_id))
        assert echo_rq.__class__ == dimsemessages.C_ECHO_RQ
        log.msg("replying")
        self.send_DIMSE_command(presentation_context_id, dimsemessages.C_ECHO_RSP(echo_rq.message_id))

    def C_FIND_RQ_received(self, presentation_context_id, find_rq, query):
        log.msg("received %s on presentation context %i" % (find_rq, presentation_context_id))

        log.msg("%s" % query)

        level = getattr(query, "QueryRetrieveLevel", "IMAGE")
        level_ids_done = set()
        
        for f in glob.glob(os.path.join(self.folder, "*.dcm*")):
            try:
                ds = dicom.read_file(f)
            except dicom.filereader.InvalidDicomError, e:
                log.err(e)
                continue

            level_id = get_level_identifier(ds, level)
            if level_id != None and level_id in level_ids_done:
                continue
            level_ids_done.add(level_id)

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

    def C_MOVE_RQ_received(self, presentation_context_id, move_rq, query):
        log.msg("received %s on presentation context %i" % (move_rq, presentation_context_id))

        log.msg("%s" % query)

        movedest = self.move_destinations.get(move_rq.move_destination)
        if movedest == None:
            log.msg("Unknown move destination AE %s." % (move_rq.move_destination,))
            self.send_DIMSE_command(presentation_context_id, 
                                    dimsemessages.C_MOVE_RSP(status = 0xA801, 
                                                             message_id_being_responded_to = move_rq.message_id,
                                                             affected_sop_class_uid = move_rq.affected_sop_class_uid))
            return
        movedest['called_ae_title'] = move_rq.move_destination

        move_rq.n_total_suboperations = 0
        move_rq.n_complete_suboperations = 0
        move_rq.n_failed_suboperations = 0

        ds_to_send = []
        
        for f in glob.glob(os.path.join(self.folder, "*.dcm*")):
            #print f
            try:
                ds = dicom.read_file(f)
            except dicom.filereader.InvalidDicomError, e:
                log.err(e)
                continue

            is_match, result_ds = match_dataset(query, ds)
            if not is_match:
                continue

            move_rq.n_total_suboperations += 1
            ds_to_send.append(ds)

        def progress_callback(store_rsp):
            move_rq.n_complete_suboperations += 1
            if store_rsp.status != 0:
                move_rq.n_failed_suboperations += 1
            if move_rq.n_total_suboperations != move_rq.n_complete_suboperations:
                self.send_DIMSE_command(presentation_context_id,
                                        dimsemessages.C_MOVE_RSP(
                                            status = 0xff00,
                                            message_id_being_responded_to = move_rq.message_id,
                                            affected_sop_class_uid = move_rq.affected_sop_class_uid,
                                            number_of_remaining_sub_operations = (
                                                move_rq.n_total_suboperations - move_rq.n_complete_suboperations - move_rq.n_failed_suboperations),
                                            number_of_completed_sub_operations = move_rq.n_complete_suboperations,
                                            number_of_failed_sub_operations = move_rq.n_failed_suboperations,
                                            number_of_warning_sub_operations = 0))
        def final_callback(status):
            self.send_DIMSE_command(
                presentation_context_id, 
                dimsemessages.C_MOVE_RSP(
                    status = 0, 
                    message_id_being_responded_to = move_rq.message_id,
                    affected_sop_class_uid = move_rq.affected_sop_class_uid,
                    number_of_remaining_sub_operations = (
                        move_rq.n_total_suboperations - move_rq.n_complete_suboperations - move_rq.n_failed_suboperations),
                        number_of_completed_sub_operations = move_rq.n_complete_suboperations,
                        number_of_failed_sub_operations = move_rq.n_failed_suboperations,
                        number_of_warning_sub_operations = 0))
            
        def errback(status):
            move_rq.n_failed_suboperations += 1
            self.send_DIMSE_command(presentation_context_id,
                                    dimsemessages.C_MOVE_RSP(
                                        status = 0xff00,
                                        message_id_being_responded_to = move_rq.message_id,
                                        affected_sop_class_uid = move_rq.affected_sop_class_uid,
                                        number_of_remaining_sub_operations = (
                                            move_rq.n_total_suboperations - move_rq.n_complete_suboperations - move_rq.n_failed_suboperations),
                                        number_of_completed_sub_operations = move_rq.n_complete_suboperations,
                                        number_of_failed_sub_operations = move_rq.n_failed_suboperations,
                                        number_of_warning_sub_operations = 0))
                

        # send dataset to movedest
        d = storescu.store(datasets = ds_to_send, 
                           host = movedest['host'], 
                           port = movedest['port'], 
                           calling_ae_title = movedest['calling_ae_title'], 
                           called_ae_title = movedest['called_ae_title'],
                           priority = move_rq.priority,
                           move_originator_application_entity_title = self.calling_ae_title,
                           move_originator_message_id = move_rq.message_id,
                           progress_callback = progress_callback)

        d.addCallback(final_callback)
        d.addErrback(errback)
        
class QRSCPFactory(Factory, object):
    def __init__(self, folder, move_destinations):
        super(QRSCPFactory, self).__init__()
        self.folder = folder
        self.move_destinations = move_destinations
    def buildProtocol(self, addr):
        protocol = QRSCP(folder = self.folder, move_destinations = self.move_destinations)
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
    endpoint.listen(QRSCPFactory(folder = sys.argv[2], move_destinations = json.load(file("move_destinations.json"))))
    reactor.run()
    log.msg("reactor.run() exited")
