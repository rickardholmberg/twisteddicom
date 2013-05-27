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

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.error import AlreadyCalled, AlreadyCancelled
from utils import get_uid

do_log = False

from functools import wraps
from twisteddicom import __version__, pdu, sockhandler

def debugrecv(f, msg=None):
    @wraps(f)
    def wrapper(*args, **kwds):
        if do_log: log.msg("upper_layer received %s" % (f.__name__.replace("_received","").replace("_","-"),))
        return f(*args, **kwds)
    return wrapper    

def debugaction(f, msg=None):
    @wraps(f)
    def wrapper(*args, **kwds):
        if do_log: log.msg("Performing action %s" % (f.__name__.replace("do_","").replace("_","-"),))
        return f(*args, **kwds)
    return wrapper

class InvalidStateError(RuntimeError):
    pass

class DICOMUpperLayerServiceProvider(sockhandler.DICOMUpperLayerServiceProtocol):
    """Handles the DICOM Upper Layer state machine and presents DICOM Upper Layer indications messages. See DICOM PS3.8-2011 9.2, esp table 9-10."""
    def __init__(self, supported_abstract_syntaxes = None, supported_transfer_syntaxes = None):
        super(DICOMUpperLayerServiceProvider, self).__init__()
        self.reject_reason = None
        self.reject_source = None
        self.reject_result = None
        self.is_association_requestor = True # Until we se an association request
        self.state = 1
        self.ARTIM_time = 10.0
        self.ARTIM = None
        if supported_abstract_syntaxes == None:
           self.supported_abstract_syntaxes = []
        else:
           self.supported_abstract_syntaxes = supported_abstract_syntaxes
        if supported_transfer_syntaxes == None:
            self.supported_transfer_syntaxes = [get_uid("Implicit VR Little Endian"),
                                                get_uid("Explicit VR Little Endian"),
                                                get_uid("Explicit VR Big Endian")]
        else:
            self.supported_transfer_syntaxes = supported_transfer_syntaxes

    def get_application_association_information(self):
        return [pdu.MaximumLengthSubitem(65536),
                pdu.ImplementationClassUIDSubitem("2.25.150550118860746082958211788772501563689"),
                pdu.ImplementationVersionNameSubitem("twstdcm" + __version__)]

    def get_presentation_contexts(self):
        return [pdu.A_ASSOCIATE_RQ.PresentationContextItem(abstract_syntax = pdu.AbstractSyntaxSubitem(abstract_syntax),
                                                           transfer_syntaxes = [pdu.TransferSyntaxSubitem(transfer_syntax) 
                                                                                for transfer_syntax in self.supported_transfer_syntaxes],
                                                           presentation_context_id = i+1)
                for i, abstract_syntax in enumerate(self.supported_abstract_syntaxes)]

    def validate_presentation_contexts(self, a_associate_rq):
        pcis = []
        for pci in a_associate_rq.presentation_context_items:
            if (self.supported_abstract_syntaxes != None and 
                pci.abstract_syntax.abstract_syntax_name not in self.supported_abstract_syntaxes):
                result_reason = 3 # abstract-syntax-not-supported (provider rejection)
            else:
                result_reason = 0
            
            pcis.append(pdu.A_ASSOCIATE_AC.PresentationContextItem(presentation_context_id = pci.presentation_context_id,
                                                                   result_reason = result_reason,
                                                                   transfer_syntax = pci.transfer_syntaxes[0]))
        return pcis

    def setstate(self, state):
        if do_log: log.msg("Going to state %i." % (state,))
        self.state = state

    def connectionMade(self):
        # This is strange here, due to twisted reporting new connections in the same way for servers and clients
        if self.state == 4:
            self.Transport_Connection_Confirmation_received()
        elif self.state == 1:
            self.Transport_Connection_Indication_received()
        else:
            raise InvalidStateError()

    def start_ARTIM(self):
        self.stop_ARTIM()
        self.ARTIM = reactor.callLater(self.ARTIM_time, self.ARTIM_expired)

    def stop_ARTIM(self):
        if self.ARTIM != None:
            try:
                self.ARTIM.cancel()
            except AlreadyCalled:
                pass
            except AlreadyCancelled:
                pass
            self.ARTIM = None

    @debugrecv
    def A_ASSOCIATE_request_received(self):
        if self.state == 1:
            self.setstate(4)
            self.do_AE_1()
        else:
            raise InvalidStateError()
    
    @debugrecv
    def Transport_Connection_Confirmation_received(self):
        if self.state == 4:
            self.setstate(5)
            self.do_AE_2()
        else:
            raise InvalidStateError()

    @debugrecv
    def Transport_Connection_Indication_received(self):
        if self.state == 1:
            self.setstate(2)
            self.do_AE_5()
        else:
            raise InvalidStateError()

    @debugrecv
    def A_ASSOCIATE_AC_PDU_received(self, data):
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 3, source = 2)
        elif self.state == 5:
            self.setstate(6)
            self.do_AE_3(data)
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_6()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_ASSOCIATE_RJ_PDU_received(self, data):
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 3, source = 2)
        elif self.state == 5:
            self.setstate(1)
            self.do_AE_4()
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_6()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_ASSOCIATE_RQ_PDU_received(self, data):
        if self.state == 2:
            self.is_association_requestor = False
            acceptable = self.is_acceptable(data)
            if acceptable:
                self.setstate(3)
            else:
                self.start_ARTIM()
                self.setstate(13)
            self.do_AE_6(data, acceptable)
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_7()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_ASSOCIATE_response_accept_received(self):
        if self.state == 3:
            self.setstate(6)
            self.do_AE_7()
        else:
            raise InvalidStateError()
            
    @debugrecv
    def A_ASSOCIATE_response_reject_received(self):
        if self.state == 3:
            self.setstate(13)
            self.do_AE_8()
        else:
            raise InvalidStateError()
            
    @debugrecv
    def P_DATA_request_received(self, data_values):
        if self.state == 6:
            self.do_DT_1(data_values)
        elif self.state == 8:
            self.do_AR_7(data_values)
        else:
            raise InvalidStateError()

    @debugrecv
    def P_DATA_TF_PDU_received(self, data):
        if do_log: log.msg("recv_P_DATA_TF_PDU")
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 3, source = 2)
        elif self.state == 6:
            self.do_DT_2(data.data_values)
        elif self.state == 7:
            self.do_AR_6(data.data_values)
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_6()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_RELEASE_request_received(self):
        if self.state == 6:
            self.setstate(7)
            self.do_AR_1()
        else:
            raise InvalidStateError()

    @debugrecv
    def A_RELEASE_RQ_PDU_received(self, data):
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 3, source = 2)
        elif self.state == 6:
            self.setstate(8)
            self.do_AR_2(data)
        elif self.state == 7:
            if self.is_association_requestor:
                self.setstate(9)
            else:
                self.setstate(10)
            self.do_AR_8()
        
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_6()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_RELEASE_RP_PDU_received(self, data):
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 3, source = 2)
        elif self.state == 7:
            self.setstate(1)
            self.do_AR_3()
        elif self.state == 10:
            self.setstate(12)
            self.do_AR_10()
        elif self.state == 11:
            self.setstate(1)
            self.do_AR_3()
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_6()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugrecv
    def A_RELEASE_response_received(self, data):
        if self.state == 8 or self.state == 12:
            self.setstate(13)
            self.do_AR_4()
        elif self.state == 9:
            self.setstate(11)
            self.do_AR_9()
        else:
            raise InvalidStateError()
    
    @debugrecv
    def A_ABORT_request_received(self, data, reason = 0):
        """For reasons, see pdu.A_ABORT."""
        if self.state == 4:
            self.setstate(1)
            self.do_AA_2()
        else:
            self.setstate(13)
            self.do_AA_1(reason_diag = reason, source = 0)

    @debugrecv
    def A_ABORT_PDU_received(self, data):
        if self.state == 2 or self.state == 13:
            self.setstate(1)
            self.do_AA_2()
        else:
            self.setstate(1)
            self.do_AA_3(reason_diag = data.reason_diag, source = data.source)

    @debugrecv
    def conn_closed_received(self):
        if self.state == 2:
            self.setstate(1)
            self.do_AA_5()
        elif self.state == 13:
            self.setstate(1)
            self.do_AR_5()
        elif self.state == 1:
            # do nothing
            pass
        else:
            self.setstate(1)
            self.do_AA_4(0)

    @debugrecv
    def ARTIM_expired(self):
        if self.state == 2 or self.state == 13:
            self.setstate(1)
            self.do_AA_2()
        else:
            raise InvalidStateError()

    @debugrecv
    def unrecognized_or_invalid_PDU_received(self, data):
        if self.state == 2:
            self.setstate(13)
            self.do_AA_1(reason_diag = 1, source = 2)
        elif self.state == 13:
            self.setstate(13)
            self.do_AA_7()
        else:
            self.setstate(13)
            self.do_AA_8()

    @debugaction
    def do_AE_1(self):
        """Issue TRANSPORT CONNECT request primitive to local transport service."""
        # assumed already done on conn
        pass

    @debugaction
    def do_AE_2(self):
        """Send A-ASSOCIATE-RQ-PDU."""
        data = pdu.A_ASSOCIATE_RQ(application_context_item = pdu.ApplicationContextItem(),
                                  called_ae_title = self.called_ae_title,
                                  calling_ae_title = self.calling_ae_title,
                                  presentation_context_items = self.get_presentation_contexts(),
                                  user_information_item = pdu.UserInformationItem(self.get_application_association_information()))
        self.presentation_contexts_requested = data.presentation_context_items
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_AE_3(self, a_associate_ac):
        """Issue A-ASSOCIATE confirmation (accept) primitive."""
        self.A_ASSOCIATE_confirmation_accept_indicated(a_associate_ac)

    @debugaction
    def do_AE_4(self):
        """Issue A-ASSOCIATE confirmation (reject) primitive and close transport connection."""
        self.A_ASSOCIATE_confirmation_reject_indicated()
        self.transport.loseConnection()

    @debugaction
    def do_AE_5(self):
        """Issue Transport connection response primitive; start ARTIM timer."""
        self.start_ARTIM()
        self.Transport_Connection_Response_indicated()

    @debugaction
    def do_AE_6(self, a_associate_rq, is_acceptable):
        """Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service-provider:
               issue A-ASSOCIATE indication primitive.
           otherwise: 
               issue A-ASSOCIATE-RJ-PDU and start ARTIM timer."""
        self.stop_ARTIM()
        if is_acceptable:
            self.A_ASSOCIATE_indicated(a_associate_rq)
        else:
            data = pdu.A_ASSOCIATE_RJ(reason_diag = self.reject_reason if self.reject_reason != None else 1,
                                      source = self.reject_source if self.reject_source else 1 if self.is_association_requestor else 2,
                                      result = self.reject_result if self.reject_result else 2) 
            if do_log: log.msg("Sending %s." % (data,))
            self.transport.write(data.pack())
            self.start_ARTIM()

    @debugaction
    def do_AE_7(self):
        """Send A-ASSOCIATE-AC PDU."""

        if do_log: log.msg("Presentation contexts active: %s" % (self.presentation_contexts_accepted,))
        data = pdu.A_ASSOCIATE_AC(application_context_item = pdu.ApplicationContextItem(),
                                  presentation_context_items = self.presentation_contexts_accepted,
                                  _reserved_called_ae_title = self.called_ae_title,
                                  _reserved_calling_ae_title = self.calling_ae_title,
                                  user_information_item = self.user_information_item_accepted)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_AE_8(self):
        """Send A-ASSOCIATE-RJ PDU and start ARTIM timer """
        data = pdu.A_ASSOCIATE_RJ(reason_diag = self.reject_reason if self.reject_reason != None else 1,
                                  source = self.reject_source if self.reject_source else 1 if self.is_association_requestor else 2,
                                  result = self.reject_result if self.reject_result else 2) 
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())
        self.start_ARTIM()

    @debugaction
    def do_DT_1(self, data_values):
        """Send P-DATA-TF PDU."""
        data = pdu.P_DATA_TF(data_values = data_values)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_DT_2(self, data):
        """Send P-DATA indication primitive."""
        self.P_DATA_indicated(data)

    @debugaction
    def do_AR_1(self):
        """Send A-RELEASE-RQ PDU."""
        data = pdu.A_RELEASE_RQ()
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_AR_2(self, a_release_rq):
        """Issue A-RELEASE indication primitive."""
        self.A_RELEASE_indicated(a_release_rq)

    @debugaction
    def do_AR_3(self):
        """Issue A-RELEASE confirmation primitive, and close transport connection."""
        self.A_RELEASE_confirmation_indicated()
        self.transport.loseConnection()

    @debugaction
    def do_AR_4(self):
        """Issue A-RELEASE-RP PDU and start ARTIM timer."""
        data = pdu.A_RELEASE_RP()
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())
        self.start_ARTIM()

    @debugaction
    def do_AR_5(self):
        """Stop ARTIM timer."""
        self.stop_ARTIM()

    @debugaction
    def do_AR_6(self, data):
        """Issue P-DATA indication."""
        self.P_DATA_indicated(data)

    @debugaction
    def do_AR_7(self, data_values):
        """Issue P-DATA-TF PDU."""
        data = pdu.P_DATA_TF(data_values = data_values)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_AR_8(self):
        """Issue A-RELEASE indication (release collision)"""
        self.A_RELEASE_release_collision_indicated()

    @debugaction
    def do_AR_9(self):
        """Send A-RELEASE-RP PDU."""
        data = pdu.A_RELEASE_RP()
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())

    @debugaction
    def do_AR_10(self):
        """Issue A-RELEASE confirmation primitive """
        self.A_RELEASE_confirmation_indicated()

    @debugaction
    def do_AA_1(self, reason_diag, source):
        """Send A-ABORT PDU (service-user source) and start (or restart if already started) ARTIM timer;."""
        data = pdu.A_ABORT(reason_diag = reason_diag, source = source)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())
        self.start_ARTIM()

    @debugaction
    def do_AA_2(self):
        """Stop ARTIM timer if running. Close transport connection."""
        self.stop_ARTIM()
        self.transport.loseConnection()
        
    @debugaction
    def do_AA_3(self, reason_diag, source):
        """If (service-user inititated abort)
               issue A-ABORT indication and close transport connection.
           otherwise (service-provider inititated abort):
               issue A-P-ABORT indication and close transport connection."""
        self.A_ABORT_confirmation_indicated(reason_diag = reason_diag, source = source)
        if source != 0: # unless service-user
            data = pdu.A_ABORT(reason_diag = reason_diag, source = source)
            if do_log: log.msg("Sending %s." % (data,))
            self.transport.write(data.pack())
        self.transport.loseConnection()
        
    @debugaction
    def do_AA_4(self, reason_diag):
        """Issue A-P-ABORT indication primitive."""
        self.A_ABORT_confirmation_indicated(reason_diag = reason_diag, source = 2)
        # This only occurs after the connection has been closed. No reason to send anything!
        # data = pdu.A_ABORT(reason_diag = reason_diag, source = 2)
        # if do_log: log.msg("Sending %s." % (data,))
        # self.transport.write(data.pack())
        
    @debugaction
    def do_AA_5(self):
        """Stop ARTIM timer."""
        self.stop_ARTIM()
        
    @debugaction
    def do_AA_6(self):
        """Ignore PDU."""
        pass
        
    @debugaction
    def do_AA_7(self):
        """Send A-ABORT PDU."""
        data = pdu.A_ABORT(reason_diag = 0, source = 0)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())
        
    @debugaction
    def do_AA_8(self):
        """Send A-ABORT PDU (service-provider source), issue an A-P-ABORT indication, and start ARTIM timer."""
        data = pdu.A_ABORT(reason_diag = 0, source = 2)
        if do_log: log.msg("Sending %s." % (data,))
        self.transport.write(data.pack())
        self.A_ABORT_confirmation_indicated(reason_diag = 0, source = 2)
        self.start_ARTIM()
        

