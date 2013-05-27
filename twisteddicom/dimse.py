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

import struct
from functools import wraps
from twisteddicom import upper_layer, dimsemessages, pdu
from twisted.python import log

do_log = False

def debugindicate(func):
    @wraps(func)
    def wrapper(*args, **kwds):
        if do_log: log.msg("DIMSE received %s" % (func.__name__.replace("_received","").replace("_","-"),))
        return func(*args, **kwds)
    return wrapper    


class DIMSEProtocol(upper_layer.DICOMUpperLayerServiceProvider):
    def __init__(self, 
                 supported_abstract_syntaxes = None, 
                 supported_transfer_syntaxes = None):
        super(DIMSEProtocol, self).__init__(supported_abstract_syntaxes = supported_abstract_syntaxes, 
                                            supported_transfer_syntaxes = supported_transfer_syntaxes)
        self.dimse_is_reading_command = True
        self.dimse_command_buffer = ""
        self.dimse_data_buffer = ""
        self.dimse_presentation_context_id = None
        self.maximum_length_sent = None
        self.presentation_contexts_requested = None
        self.presentation_contexts_accepted = None
        self.user_information_item_accepted = None
        self.dimse_command_buffer = ""
        self.dimse_command = None
        self.dimse_data_buffer = ""
        self.dimse_is_reading_command = True
        self.dimse_presentation_context_id = None

    called_ae_title = "CALLED"
    calling_ae_title = "CALLING"

    def send_DIMSE_command(self, presentation_context_id, dimse_command, dimse_data = None):
        if do_log: log.msg("sending DIMSE command %s on context %s" % (dimse_command, presentation_context_id))
        dimse_command_pack = dimse_command.pack()
        dimse_command_len = 6 + len(dimse_command_pack) 
        if dimse_data != None:
            ts = [pci.transfer_syntaxes[0].transfer_syntax_name 
                  for pci in self.presentation_contexts_requested 
                  if pci.presentation_context_id == presentation_context_id][0]
            
            dimse_data_pack = dimsemessages.pack_dataset(dimse_data, dimsemessages.is_implicit_VR(ts), 
                                                         dimsemessages.is_little_endian(ts))
            dimse_data_len = 6 + len(dimse_data_pack)
        else:
            dimse_data_pack = ''
            dimse_data_len = 0

        if do_log: log.msg("maximum_length_sent = %s" % (self.maximum_length_sent,))
        if self.maximum_length_sent == None or self.maximum_length_sent >= dimse_command_len + dimse_data_len:
            messages = [(presentation_context_id, '\x03' + dimse_command_pack)]
            if dimse_data != None:
                messages.append((presentation_context_id, '\x02' + dimse_data_pack))
            self.P_DATA_request_received(messages)
        else:
            while dimse_command_pack != '':
                fits = dimse_command_pack[:self.maximum_length_sent - 6 & ~1]
                dimse_command_pack = dimse_command_pack[self.maximum_length_sent - 6 & ~1:]
                if dimse_command_pack == '':
                    messages = [(presentation_context_id, '\x03' + fits)]
                else:
                    messages = [(presentation_context_id, '\x01' + fits)]
                self.P_DATA_request_received(messages)

            while dimse_data_pack != '':
                fits = dimse_data_pack[:self.maximum_length_sent - 6 & ~1]
                dimse_data_pack = dimse_data_pack[self.maximum_length_sent - 6 & ~1:]
                if dimse_data_pack == '':
                    messages = [(presentation_context_id, '\x02' + fits)]
                else:
                    messages = [(presentation_context_id, '\x00' + fits)]
                self.P_DATA_request_received(messages)

    def is_acceptable(self, a_associate_rq):
        # At least one presentation context has to be requested.
        if len(a_associate_rq.presentation_context_items) > 0:
            return True
        else:
            return False
    
    @debugindicate
    def A_ASSOCIATE_confirmation_accept_indicated(self, a_associate_ac):
        """Called from upper_layer.do_AE_3 when a remote system has sent A_ASSOCIATE_AC."""
        self.presentation_contexts_accepted = a_associate_ac.presentation_context_items
        self.user_information_item_accepted = a_associate_ac.user_information_item
        if a_associate_ac.user_information_item != None:
            for user_data in a_associate_ac.user_information_item.user_data_subitems:
                if isinstance(user_data, pdu.MaximumLengthSubitem):
                    if user_data.maximum_length_received != 0:
                        self.maximum_length_sent = user_data.maximum_length_received
                    else:
                        self.maximum_length_sent = None

    @debugindicate
    def A_ASSOCIATE_confirmation_reject_indicated(self):
        pass
        
    @debugindicate
    def A_RELEASE_confirmation_indicated(self):
        pass

    @debugindicate
    def A_RELEASE_indicated(self, a_release_rq):
        """Called by application when it's time to release the
        association and eventually disconnect.

        Just pass it on to upper_layer."""
        self.A_RELEASE_response_received(a_release_rq)

    @debugindicate
    def A_ASSOCIATE_indicated(self, a_associate_rq):
        """Called from upper_layer.do_AE_6 when a remote system has
        send an acceptable associate request.  

        Select which presentation contexts to accept, and then pass it
        on to upper_layer.A_ASSOCIATE_response_accept_received to send
        an accept message to the remote system."""

        self.presentation_contexts_requested = a_associate_rq.presentation_context_items
        self.presentation_contexts_accepted = self.validate_presentation_contexts(a_associate_rq)
        self.user_information_item_accepted = pdu.UserInformationItem(self.get_application_association_information())
        
        self.A_ASSOCIATE_response_accept_received()

    @debugindicate
    def P_DATA_indicated(self, data_values):
        for val in data_values:
            msg_ctrl_hdr, = struct.unpack("B", val[1][0])
            if self.dimse_presentation_context_id != None:
                if val[0] != self.dimse_presentation_context_id:
                    log.err("Got unexpected interleaved presentation contexts in data stream")
                    self.A_ABORT_request_received(None, reason = 6)
                    return

            accepted = [pci.result_reason == 0 
                        for pci in self.presentation_contexts_accepted 
                        if pci.presentation_context_id == val[0]]

            if accepted != [True]:
                self.A_ABORT_request_received(None, reason = 6)
                return
                
            self.dimse_presentation_context_id = val[0]
            
            ts = [pci.transfer_syntaxes[0].transfer_syntax_name 
                  for pci in self.presentation_contexts_requested 
                  if pci.presentation_context_id == self.dimse_presentation_context_id][0]
            if self.dimse_is_reading_command:
                assert msg_ctrl_hdr & 1, "Got data type pdv while reading command!"
                self.dimse_command_buffer += val[1][1:]
                if msg_ctrl_hdr & 2: # End of command
                    self.dimse_command = dimsemessages.unpack_dataset(self.dimse_command_buffer)
                    if do_log: log.msg("revcommand: %s" % (dimsemessages.revcommands[self.dimse_command.CommandField],))
                    if getattr(self.dimse_command, 'CommandDataSetType', 0) == 0x101:
                        self.dimse_is_reading_command = True
                        cmd = dimsemessages.unpack_dimse_command(self.dimse_command)
                        self.DIMSE_command_received(self.dimse_presentation_context_id, cmd, None)
                        self.dimse_command_buffer = ""
                        self.dimse_command = None
                        self.dimse_presentation_context_id = None
                    else:
                        self.dimse_is_reading_command = False
            else:
                assert not msg_ctrl_hdr & 1, "Got command type pdv while reading data!"
                self.dimse_data_buffer += val[1][1:]
                if msg_ctrl_hdr & 2: # End of data
                    dimse_data = dimsemessages.unpack_dataset(self.dimse_data_buffer, ts)
                    cmd = dimsemessages.unpack_dimse_command(self.dimse_command)
                    self.DIMSE_command_received(self.dimse_presentation_context_id, cmd, dimse_data)
                    self.dimse_command_buffer = ""
                    self.dimse_command = None
                    self.dimse_data_buffer = ""
                    self.dimse_is_reading_command = True
                    self.dimse_presentation_context_id = None

    def DIMSE_command_received(self, presentation_context_id, cmd, data):
        if cmd.__class__ == dimsemessages.C_STORE_RQ:
            self.C_STORE_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_STORE_RSP:
            self.C_STORE_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_GET_RQ:
            self.C_GET_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_GET_RSP:
            self.C_GET_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_FIND_RQ:
            self.C_FIND_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_FIND_RSP:
            self.C_FIND_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_MOVE_RQ:
            self.C_MOVE_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_MOVE_RSP:
            self.C_MOVE_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_ECHO_RQ:
            self.C_ECHO_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_ECHO_RSP:
            self.C_ECHO_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_EVENT_REPORT_RQ:
            self.N_EVENT_REPORT_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_EVENT_REPORT_RSP:
            self.N_EVENT_REPORT_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_GET_RQ:
            self.N_GET_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_GET_RSP:
            self.N_GET_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_SET_RQ:
            self.N_SET_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_SET_RSP:
            self.N_SET_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_ACTION_RQ:
            self.N_ACTION_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_ACTION_RSP:
            self.N_ACTION_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_CREATE_RSP:
            self.N_CREATE_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_DELETE_RQ:
            self.N_DELETE_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_DELETE_RSP:
            self.N_DELETE_RSP_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.N_CREATE_RQ:
            self.N_CREATE_RQ_received(presentation_context_id, cmd, data)
        elif cmd.__class__ == dimsemessages.C_CANCEL_RQ:
            self.C_CANCEL_RQ_received(presentation_context_id, cmd, data)
        else:            
            self.unrecognized_or_invalid_DIMSE_received(presentation_context_id, cmd, data)

    def C_STORE_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_STORE_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_GET_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_GET_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_FIND_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_FIND_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_MOVE_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_MOVE_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_ECHO_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_ECHO_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_EVENT_REPORT_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_EVENT_REPORT_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_GET_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_GET_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_SET_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_SET_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_ACTION_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_ACTION_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_CREATE_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_DELETE_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_DELETE_RSP_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def N_CREATE_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def C_CANCEL_RQ_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
    def unrecognized_or_invalid_DIMSE_received(self, presentation_context_id, cmd, data):
        raise NotImplementedError
