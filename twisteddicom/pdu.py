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
from twisted.python import log

do_log = False

def _unpack_H_string(s, offset):
    l, = struct.unpack_from("!H", s, offset)
    return s[offset+2:offset+2+l], offset + 2 + l

class PDU(object):
    def __len__(self):
        return self.header_size + self.pdu_length

    @classmethod
    def unpack(cls, buffer, current_offset = 0):
        if len(buffer) < current_offset + 2:
            return current_offset, None
        pdu_type, = struct.unpack("B", buffer[current_offset])
        pdu_header_length = pdus[pdu_type].header_size
        header_end = current_offset + pdu_header_length
        if len(buffer) < header_end:
            return current_offset, None
        pdu_type, reserved, pdu_length = struct.unpack(pdus[pdu_type].header, 
                                                       buffer[current_offset : header_end])

        pdu_end = header_end + pdu_length
        if len(buffer) < pdu_end:
            return current_offset, None
        data = pdus[pdu_type]()
        data.unpack(buffer[current_offset : pdu_end])
        return pdu_end, data

    
class A_ASSOCIATE_RQ(PDU):
    """A-ASSOCIATE-RQ PDU STRUCTURE - See DICOM PS3.8-2011 9.3.2"""
    pdu_type = 0x01
    header = "!BBI"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!HH", self.protocol_version, 0)
        s += bytes(self.called_ae_title.ljust(16))
        s += bytes(self.calling_ae_title.ljust(16))
        s += b'\x00' * 32
        s += self.application_context_item.pack()
        for pci in self.presentation_context_items:
            assert isinstance(pci, A_ASSOCIATE_RQ.PresentationContextItem)
        s += "".join((x.pack() for x in self.presentation_context_items))
        s += self.user_information_item.pack()
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        protocol_version, reserved = struct.unpack_from("!HH", s, i)
        i += 4
        assert protocol_version & 1 == 1
        self.called_ae_title = s[i:i+16].rstrip()
        i += 16
        self.calling_ae_title = s[i:i+16].rstrip()
        i += 16
        i += 32
        self.application_context_item = ApplicationContextItem()
        i += self.application_context_item.unpack(s, i)
        self.presentation_context_items = []
        while struct.unpack("B", s[i])[0] == A_ASSOCIATE_RQ.PresentationContextItem.pdu_type:
            self.presentation_context_items.append(A_ASSOCIATE_RQ.PresentationContextItem())
            i += self.presentation_context_items[-1].unpack(s, i)
        self.user_information_item = UserInformationItem()
        i += self.user_information_item.unpack(s, i)
        assert pdu_length == self.pdu_length
        assert pdu_length == i - 6 - offset
        return i - offset

    @property
    def protocol_version(self):
        return 1

    @property
    def pdu_length(self):
        return 68 + len(self.application_context_item) + sum(len(x) for x in self.presentation_context_items) + len(self.user_information_item)

    def __init__(self, application_context_item = None, called_ae_title = None, calling_ae_title = None, presentation_context_items = None, user_information_item = None):
        self.application_context_item = application_context_item
        self.called_ae_title = called_ae_title
        self.calling_ae_title = calling_ae_title
        self.presentation_context_items = presentation_context_items
        self.user_information_item = user_information_item

    def __repr__(self):
        return "<A_ASSOCIATE_RQ application_context_item = %s, called_ae_title = %s, calling_ae_title = %s, presentation_context_items = %s, user_information_item = %s>" % (self.application_context_item, self.called_ae_title, self.calling_ae_title, self.presentation_context_items, self.user_information_item)
            

    class PresentationContextItem(PDU):
        """Presentation context item structure - See DICOM PS3.8-2011 9.3.2.2"""
        pdu_type = 0x20
        header = "!BBH"
        header_size = struct.calcsize(header)

        def pack(self):
            s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
            s += struct.pack("!BBBB", self.presentation_context_id, 0, 0, 0)
            s += self.abstract_syntax.pack()
            s += "".join((x.pack() for x in self.transfer_syntaxes))
            return s

        def unpack(self, s, offset = 0):
            i = offset
            pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
            i += self.header_size
            assert pdu_type == self.pdu_type
            self.presentation_context_id, reserved, reserved, reserved = struct.unpack_from("!BBBB", s, i)
            i += 4
            self.abstract_syntax = AbstractSyntaxSubitem()
            i += self.abstract_syntax.unpack(s, i)
            self.transfer_syntaxes = []
            while i - 4 - offset < item_length:
                self.transfer_syntaxes.append(TransferSyntaxSubitem())
                i += self.transfer_syntaxes[-1].unpack(s, i)
            assert item_length == self.pdu_length
            assert item_length == i - 4 - offset
            return i - offset

        @property
        def pdu_length(self):
            return 4 + len(self.abstract_syntax.pack()) + sum(len(x.pack()) for x in self.transfer_syntaxes)
          
        def __init__(self, abstract_syntax = None, presentation_context_id = None, transfer_syntaxes = None):
            self.abstract_syntax = abstract_syntax
            self.presentation_context_id = presentation_context_id
            self.transfer_syntaxes = transfer_syntaxes

        def __repr__(self):
            return "<A_ASSOCIATE_RQ.PresentationContextItem abstract_syntax = %s, presentation_context_id = %s, transfer_syntaxes = %s>" % (self.abstract_syntax, self.presentation_context_id, self.transfer_syntaxes)
                

    class UserIdentitySubitem(PDU):
        """User Identity sub-item structure(A-ASSOCIATE-RQ) - See DICOM PS3.7-2011 D.3.3.7.1."""
        pdu_type = 0x58
        header = "!BBH"
        header_size = struct.calcsize(header)

        def pack(self):
            s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
            s += struct.pack("!BB", self.user_identity_type, self.positive_response_requested)
            s += struct.pack("!H", len(self.primary_field)) + self.primary_field
            if self.user_identity_type == 2:
                s += struct.pack("!H", len(self.secondary_field)) + self.secondary_field
            return s

        def unpack(self, s, offset = 0):
            i = offset
            pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
            i += self.header_size
            assert pdu_type == self.pdu_type
            self.user_identity_type, self.positive_response_requested = struct.unpack_from("!BB", s, i)
            i += 2
            self.primary_field, i = _unpack_H_string(s, i)
            if self.user_identity_type == 2:
                self.secondary_field, i = _unpack_H_string(s, i)
            else:
                self.secondary_field = None
            assert item_length == self.pdu_length
            assert item_length == i - 4 - offset
            return i - offset

        @property
        def pdu_length(self):
            i = 2 + 2 + len(self.primary_field)
            if self.user_identity_type == 2:
                i += 2 + len(self.secondary_field)
            return i

        def __init__(self, positive_response_requested = None, primary_field = None, secondary_field = None, user_identity_type = None):
            self.positive_response_requested = positive_response_requested
            self.primary_field = primary_field
            self.secondary_field = secondary_field
            self.user_identity_type = user_identity_type

        def __repr__(self):
            return "<A_ASSOCIATE_RQ.UserIdentitySubitem positive_response_requested = %s, primary_field = %s, secondary_field = %s, user_identity_type = %s>" % (self.positive_response_requested, self.primary_field, self.secondary_field, self.user_identity_type)
                

        
class A_ASSOCIATE_AC(PDU):
    """A-ASSOCIATE-AC PDU STRUCTURE - See DICOM PS3.8-2011 9.3.3."""
    pdu_type = 0x02
    header = "!BBI"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!HH", self.protocol_version, 0)
        s += self._reserved_called_ae_title.ljust(16)
        s += self._reserved_calling_ae_title.ljust(16)
        s += '\x00' * 32
        s += self.application_context_item.pack()
        for pci in self.presentation_context_items:
            assert isinstance(pci, A_ASSOCIATE_AC.PresentationContextItem)
        s += "".join((x.pack() for x in self.presentation_context_items))
        s += self.user_information_item.pack()
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        protocol_version, reserved = struct.unpack_from("!HH", s, i)
        i += 4
        assert protocol_version & 1 == 1
        self._reserved_called_ae_title = s[i:i+16].rstrip()
        i += 16
        self._reserved_calling_ae_title = s[i:i+16].rstrip()
        i += 16
        i += 32
        self.application_context_item = ApplicationContextItem()
        i += self.application_context_item.unpack(s, i)
        self.presentation_context_items = []
        while struct.unpack("B", s[i])[0] == A_ASSOCIATE_AC.PresentationContextItem.pdu_type:
            self.presentation_context_items.append(A_ASSOCIATE_AC.PresentationContextItem())
            i += self.presentation_context_items[-1].unpack(s, i)
        self.user_information_item = UserInformationItem()
        i += self.user_information_item.unpack(s, i)
        assert pdu_length == self.pdu_length
        assert pdu_length == i - 6 - offset
        return i - offset

    @property
    def protocol_version(self):
        return 1

    @property
    def pdu_length(self):
        return 68 + len(self.application_context_item) + sum(len(x) for x in self.presentation_context_items) + len(self.user_information_item)

    def __init__(self, application_context_item = None, presentation_context_items = None, _reserved_called_ae_title = "", _reserved_calling_ae_title = "", user_information_item = None):
        self.application_context_item = application_context_item
        self.presentation_context_items = presentation_context_items
        self._reserved_called_ae_title = _reserved_called_ae_title
        self._reserved_calling_ae_title = _reserved_calling_ae_title
        self.user_information_item = user_information_item

    def __repr__(self):
        return "<A_ASSOCIATE_AC application_context_item = %s, presentation_context_items = %s, _reserved_called_ae_title = %s, _reserved_calling_ae_title = %s, user_information_item = %s>" % (self.application_context_item, self.presentation_context_items, self._reserved_called_ae_title, self._reserved_calling_ae_title, self.user_information_item)

    class PresentationContextItem(PDU):
        """Presentation context item structure - See DICOM PS3.8-2011 9.3.2.2"""
        pdu_type = 0x21
        header = "!BBH"
        header_size = struct.calcsize(header)
        _results_reasons = {
            0: "acceptance",
            1: "user-rejection",
            2: "no-reason (provider rejection)",
            3: "abstract-syntax-not-supported (provider rejection)",
            4: "transfer-syntaxes-not-supported (provider rejection)",
            }

        def pack(self):
            s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
            s += struct.pack("!BBBB", self.presentation_context_id, 0, self.result_reason, 0)
            s += self.transfer_syntax.pack()
            return s

        def unpack(self, s, offset = 0):
            i = offset
            pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
            i += self.header_size
            assert pdu_type == self.pdu_type
            self.presentation_context_id, reserved, self.result_reason, reserved = struct.unpack_from("!BBBB", s, i)
            i += 4
            self.transfer_syntax = TransferSyntaxSubitem()
            i += self.transfer_syntax.unpack(s, i)
            assert item_length == self.pdu_length
            assert item_length == i - 4 - offset
            return i - offset

        @property
        def pdu_length(self):
            return 4 + len(self.transfer_syntax.pack())
          
        def __init__(self, presentation_context_id = None, result_reason = None, transfer_syntax = None):
            self.presentation_context_id = presentation_context_id
            self.result_reason = result_reason
            self.transfer_syntax = transfer_syntax

        def __repr__(self):
            return "<A_ASSOCIATE_AC.PresentationContextItem presentation_context_id = %s, result_reason = %s (%s), transfer_syntax = %s>" % (self.presentation_context_id, self.result_reason, self._results_reasons.get(self.result_reason, "??"), self.transfer_syntax)

    class UserIdentitySubitem(PDU):
        """User Identity sub-item structure(A-ASSOCIATE-AC) - See DICOM PS3.7-2011 D.3.3.7.2."""
        pdu_type = 0x59
        header = "!BBH"
        header_size = struct.calcsize(header)

        def pack(self):
            s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
            s += struct.pack("!H", len(self.server_response)) + self.server_response
            return s

        def unpack(self, s, offset = 0):
            i = offset
            pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
            i += self.header_size
            assert pdu_type == self.pdu_type
            self.server_response, i = _unpack_H_string(s, i)
            assert item_length == self.pdu_length
            assert item_length == i - 4 - offset
            return i - offset
            
        @property
        def pdu_length(self):
            return 2 + len(self.server_response)

        def __init__(self, server_response = None):
            self.server_response = server_response

        def __repr__(self):
            return "<A_ASSOCIATE_AC.UserIdentitySubitem server_response = %s>" % (self.server_response)
                
    
class ApplicationContextItem(PDU):
    """Application context item structure - See DICOM PS3.8-2011 9.3.2.1"""
    pdu_type = 0x10
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += self.application_context_name
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.application_context_name = s[i:i+item_length]
        i += item_length
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return len(self.application_context_name)
      
    def __init__(self, application_context_name = "1.2.840.10008.3.1.1.1"):
        self.application_context_name = application_context_name

    def __repr__(self):
        return "<ApplicationContextItem application_context_name = %s>" % (self.application_context_name)
            

class AbstractSyntaxSubitem(PDU):
    """Abstract syntax sub-item structure - See DICOM PS3.8-2011 9.3.2.2.1"""
    pdu_type = 0x30
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += self.abstract_syntax_name
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.abstract_syntax_name = s[i:i+item_length]
        i += item_length
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return len(self.abstract_syntax_name)

    def __init__(self, abstract_syntax_name = None):
        self.abstract_syntax_name = abstract_syntax_name

    def __repr__(self):
        return "<AbstractSyntaxSubitem abstract_syntax_name = %s>" % (self.abstract_syntax_name)
            

class TransferSyntaxSubitem(PDU):
    """Transfer syntax sub-item structure - See DICOM PS3.8-2011 9.3.2.2.2"""
    pdu_type = 0x40
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += self.transfer_syntax_name
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.transfer_syntax_name = s[i:i+item_length]
        i += item_length
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return len(self.transfer_syntax_name)

    def __init__(self, transfer_syntax_name = None):
        self.transfer_syntax_name = transfer_syntax_name

    def __repr__(self):
        return "<TransferSyntaxSubitem transfer_syntax_name = %s>" % (self.transfer_syntax_name)
            

class UserInformationItem(PDU):
    """User information item structure - See DICOM PS3.8-2011 9.3.2.3"""
    pdu_type = 0x50
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += "".join((x.pack() for x in self.user_data_subitems))
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        if do_log: log.msg("self.pdu_type: %x, data.pdu_type: %x" % (self.pdu_type, pdu_type))
        assert pdu_type == self.pdu_type
        self.user_data_subitems = []
        while i - 4 - offset < item_length:
            item_type, = struct.unpack("B", s[i])
            self.user_data_subitems.append(pdus[item_type]())
            i += self.user_data_subitems[-1].unpack(s, i)
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return sum(len(x) for x in self.user_data_subitems)
      
    def __init__(self, user_data_subitems = None):
        self.user_data_subitems = user_data_subitems

    def __repr__(self):
        return "<UserInformationItem user_data_subitems = %s>" % (self.user_data_subitems)
            

class MaximumLengthSubitem(PDU):
    """Maximum length sub-item structure (A-ASSOCIATE-RQ/AC) - See DICOM PS3.8-2011 D.1"""
    pdu_type = 0x51
    header = "!BBH"
    header_size = struct.calcsize(header)
    
    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!I", self.maximum_length_received)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size

        self.maximum_length_received, = struct.unpack_from("!I", s, i)
        i += 4
        assert pdu_type == self.pdu_type
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 4
      
    def __init__(self, maximum_length_received = None):
        self.maximum_length_received = maximum_length_received

    def __repr__(self):
        return "<MaximumLengthSubitem maximum_length_received = %s>" % (self.maximum_length_received)
            

class ImplementationClassUIDSubitem(PDU):
    """Implementation class UID sub-item structure (A-ASSOCIATE-RQ/AC) - See DICOM PS3.7-2011 D.3.3.2.1 and D.3.3.2.2."""
    pdu_type = 0x52
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += self.implementation_class_uid
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.implementation_class_uid = s[i:i+item_length]
        i += item_length
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return len(self.implementation_class_uid)

    def __init__(self, implementation_class_uid = None):
        self.implementation_class_uid = implementation_class_uid

    def __repr__(self):
        return "<ImplementationClassUIDSubitem implementation_class_uid = %s>" % (self.implementation_class_uid)
            

class ImplementationVersionNameSubitem(PDU):
    """Implementation Version Name sub-item structure (A-ASSOCIATE-RQ/AC) - See DICOM PS3.7-2011 D.3.3.2.3 and D.3.3.2.4."""
    pdu_type = 0x55
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += self.implementation_version_name
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.implementation_version_name = s[i:i+item_length]
        i += item_length
        assert item_length == self.pdu_length, "item_length = %s, self.pdu_length = %s in %s, s = %s" % (item_length, self.pdu_length, self, s)
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return len(self.implementation_version_name)
      
    def __init__(self, implementation_version_name = None):
        self.implementation_version_name = implementation_version_name

    def __repr__(self):
        return "<ImplementationVersionNameSubitem implementation_version_name = %s>" % (self.implementation_version_name)
            

class AsynchronousOperationsWindowSubitem(PDU):
    """Asynchronous operations window sub-item structure (A-ASSOCIATE-RQ/AC) - See DICOM PS3.7-2011 D.3.3.3.1 and D.3.3.3.2."""
    pdu_type = 0x53
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!HH", self.maximum_number_operations_invoked, self.maximum_number_operations_performed)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.maximum_number_operations_invoked, self.maximum_number_operations_performed = struct.unpack_from("!HH", s, i)
        i += 4
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 4
    
    def __init__(self, maximum_number_operations_invoked = None, maximum_number_operations_performed = None):
        self.maximum_number_operations_invoked = maximum_number_operations_invoked
        self.maximum_number_operations_performed = maximum_number_operations_performed

    def __repr__(self):
        return "<AsynchronousOperationsWindowSubitem maximum_number_operations_invoked = %s, maximum_number_operations_performed = %s>" % (self.maximum_number_operations_invoked, self.maximum_number_operations_performed)
            

class SCPSCURoleSelectionSubitem(PDU):
    """SCP/SCU Role selection sub-item structure (A-ASSOCIATE-RQ/AC) - See DICOM PS3.7-2011 D.3.3.4.1 and D.3.3.4.2.."""
    pdu_type = 0x54
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!H", len(self.sop_class_uid)) + self.sop_class_uid
        s += struct.pack("!BB", self.scu_role, self.scp_role)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.sop_class_uid, i = _unpack_H_string(s, i)
        self.scu_role, self.scp_role = struct.unpack_from("!BB", s, i)
        i += 2
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 2 + len(self.sop_class_uid) + 2
    
    def __init__(self, scp_role = None, scu_role = None, sop_class_uid = None):
        self.scp_role = scp_role
        self.scu_role = scu_role
        self.sop_class_uid = sop_class_uid

    def __repr__(self):
        return "<SCPSCURoleSelectionSubitem scp_role = %s, scu_role = %s, sop_class_uid = %s>" % (self.scp_role, self.scu_role, self.sop_class_uid)
            

    

class SOPClassExtendedNegotiationSubitem(PDU):
    """SOP class extended negotiation sub-item structure(A-ASSOCIATE-RQ/AC) - See DICOM PS3.7-2011 D.3.3.5.1 and D.3.3.5.2."""
    pdu_type = 0x56
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!H", len(self.sop_class_uid)) + self.sop_class_uid
        s += self.service_class_application_information
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.sop_class_uid, i = _unpack_H_string(s, i)
        self.service_class_application_information = s[i:offset+item_length+4]
        i = offset + item_length + 4
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 2 + len(self.sop_class_uid) + len(self.service_class_application_information)

    def __init__(self, service_class_application_information = None, sop_class_uid = None):
        self.service_class_application_information = service_class_application_information
        self.sop_class_uid = sop_class_uid

    def __repr__(self):
        return "<SOPClassExtendedNegotiationSubitem service_class_application_information = %s, sop_class_uid = %s>" % (self.service_class_application_information, self.sop_class_uid)
            

class SOPClassCommonExtendedNegotiationSubitem(PDU):
    """SOP class common extended negotiation sub-item structure (A-ASSOCIATE-RQ) - See DICOM PS3.7-2011 - D.3.3.6.1 and D.3.3.6.2."""
    pdu_type = 0x57
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!H", len(self.sop_class_uid)) + self.sop_class_uid
        s += struct.pack("!H", len(self.service_class_uid)) + self.service_class_uid
        s += struct.pack("!H", sum(2+len(x) for x in self.related_general_sop_class_identification))
        s += "".join(struct.pack("!H", len(x)) + x for x in self.related_general_sop_class_identification)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.sop_class_uid, i = _unpack_H_string(s, i)
        self.service_class_uid, i = _unpack_H_string(s, i)
        j, = struct.unpack_from("!H", s, i)
        i += 2
        j += i
        self.related_general_sop_class_identification = []
        while i < j:
            x, i = _unpack_H_string(s, i)
            self.related_general_sop_class_identification.append(x)
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return (2 + len(self.sop_class_uid) +
                2 + len(self.service_class_uid) +
                2 + sum(2+len(x) for x in self.related_general_sop_class_identification))

    def __init__(self, related_general_sop_class_identification = None, service_class_uid = None, sop_class_uid = None):
        self.related_general_sop_class_identification = related_general_sop_class_identification
        self.service_class_uid = service_class_uid
        self.sop_class_uid = sop_class_uid

    def __repr__(self):
        return "<SOPClassCommonExtendedNegotiationSubitem related_general_sop_class_identification = %s, service_class_uid = %s, sop_class_uid = %s>" % (self.related_general_sop_class_identification, self.service_class_uid, self.sop_class_uid)
            

class A_ASSOCIATE_RJ(PDU):
    """A-ASSOCIATE-RJ PDU Structure - See DICOM PS3.8-2011 9.3.4."""
    pdu_type = 0x03
    header = "!BBI"
    header_size = struct.calcsize(header)

    _reasons = {
        (1,1): "no-reason-given",
        (1,2): "application-context-name-not-supported",
        (1,3): "calling-AE-title-not-recognized",
        (1,4): "reserved",
        (1,5): "reserved",
        (1,6): "reserved",
        (1,7): "called-AE-title-not-recognized",
        (1,8): "reserved",
        (1,9): "reserved",
        (1,10): "reserved",
        (2,1): "no-reason-given",
        (2,2): "protocol-version-not-supported",
        (3,0): "reserved",
        (3,1): "temporary-congestion",
        (3,2): "local-limit-exceeded",
        (3,3): "reserved",
        (3,4): "reserved",
        (3,5): "reserved",
        (3,6): "reserved",
        (3,7): "reserved",
        }

    _results = {1: "rejected-permanent",
               2: "rejected-transient"}

    _sources = {1: "DICOM UL service-user",
                2: "DICOM UL service-provider (ACSE related function)",
                3: "DICOM UL service-provider (Presentation related function)"}


    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!BBBB", 0, self.result, self.source, self.reason_diag)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        reserved, self.result, self.source, self.reason_diag = struct.unpack_from("!BBBB", s, i)
        i += 4
        assert pdu_length == self.pdu_length
        assert pdu_length == i - 6 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 4


    def __init__(self, reason_diag = None, result = None, source = None):
        self.reason_diag = reason_diag
        self.result = result
        self.source = source

    def __repr__(self):
        return "<A_ASSOCIATE_RJ reason_diag = %s (%s), result = %s (%s), source = %s (%s)>" % (self.reason_diag, self._reasons.get((self.source, self.reason_diag), "??"), self.result, self._results.get(self.result, "??"), self.source, self._sources.get(self.source, "??"))
            
class P_DATA_TF(PDU):
    """P-DATA-TF PDU STRUCTURE - See DICOM PS3.8-2011 9.3.5."""
    pdu_type = 0x04
    header = "!BBI"
    header_size = struct.calcsize(header)
    
    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        for presentation_context_id, presentation_data_value in self.data_values:
            s += struct.pack("!IB", 1 + len(presentation_data_value), presentation_context_id) + presentation_data_value
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        self.data_values = []
        while i - 6 - offset < pdu_length:
            item_length, presentation_context_id = struct.unpack_from("!IB", s, i)
            i += 5
            presentation_data_value = s[i:i+item_length-1]
            i += item_length-1
            self.data_values.append((presentation_context_id, presentation_data_value))
        assert pdu_length == self.pdu_length
        assert pdu_length == i - 6 - offset
        return i - offset

    @property
    def pdu_length(self):
        return sum(5 + len(val) for cid,val in self.data_values)

    def __init__(self, data_values = None):
        self.data_values = data_values

    def __repr__(self):
        def shorten(x):
            if len(x) < 50:
                data_rep = x
            else:
                data_rep = x[:20] + " ... " + x[-20:]
            return data_rep
        data_reps = [(x, shorten(y)) for x,y in self.data_values]
        return "<P_DATA_TF data_values = %s, pdu_length = %s>" % (data_reps, self.pdu_length)
            
class A_RELEASE_RQ(PDU):
    """A-RELEASE-RQ PDU Structure - See DICOM PS3.8-2011 9.3.6."""
    pdu_type = 0x05
    header = "!BBI"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!I", 0)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        reserved, = struct.unpack_from("!I", s, i)
        i += 4
        assert pdu_length == i - 6 - offset
        assert pdu_length == self.pdu_length
        return i - offset

    @property
    def pdu_length(self):
        return 4


    def __init__(self):
        pass

    def __repr__(self):
        return "<A_RELEASE_RQ>"
        
class A_RELEASE_RP(PDU):
    """A-RELEASE-RP PDU Structure - See DICOM PS3.8-2011 9.3.7."""
    pdu_type = 0x06
    header = "!BBI"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!I", 0)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        reserved, = struct.unpack_from("!I", s, i)
        i += 4
        assert pdu_length == i - 6 - offset
        assert pdu_length == self.pdu_length
        return i - offset

    @property
    def pdu_length(self):
        return 4

    def __init__(self):
        pass

    def __repr__(self):
        return "<A_RELEASE_RP>"
        

class A_ABORT(PDU):
    """A-ABORT PDU Structure - See DICOM PS3.8-2011 9.3.8."""
    pdu_type = 0x07
    header = "!BBI"
    header_size = struct.calcsize(header)

    _sources = {
        0: "DICOM UL service-user (initiated abort)",
        1: "reserved",
        2: "DICOM UL service-provider (initiated abort)",
        }
    _reasons_diags = {
        0: "reason-not-specified",
        1: "unrecognized-PDU",
        2: "unexpected-PDU",
        3: "reserved",
        4: "unrecognized-PDU parameter",
        5: "unexpected-PDU parameter",
        6: "invalid-PDU-parameter value",
        }

    def pack(self):
        s = struct.pack("!BBI", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!BBBB", 0, 0, self.source, self.reason_diag)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, pdu_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        assert pdu_type == self.pdu_type
        reserved, reserved, self.source, self.reason_diag = struct.unpack_from("!BBBB", s, i)
        i += 4
        assert pdu_length == self.pdu_length
        assert pdu_length == i - 6 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 4

    def __init__(self, reason_diag = None, source = None):
        self.reason_diag = reason_diag
        self.source = source

    def __repr__(self):
        return "<A_ABORT reason_diag = %s (%s), source = %s (%s)>" % (self.reason_diag, self._reasons_diags.get(self.reason_diag, "??"), self.source, self._sources.get(self.source, "??"))

class DummyItem(PDU):
    """Dummy Item - only for testing"""
    pdu_type = 0xFF
    header = "!BBH"
    header_size = struct.calcsize(header)

    def pack(self):
        s = struct.pack("!BBH", self.pdu_type, 0, self.pdu_length)
        s += struct.pack("!I", self.dummy_id)
        return s

    def unpack(self, s, offset = 0):
        i = offset
        pdu_type, reserved, item_length = struct.unpack_from(self.header, s, i)
        i += self.header_size
        self.dummy_id, = struct.unpack_from("!I", s, i)
        i += 4
        if do_log: log.msg("dummy item unpacked with id %s" % (self.dummy_id,))
        assert pdu_type == self.pdu_type
        assert item_length == self.pdu_length
        assert item_length == i - 4 - offset
        return i - offset

    @property
    def pdu_length(self):
        return 4
      
    def __init__(self, dummy_id = 0):
        self.dummy_id = dummy_id

    def __repr__(self):
        return "<DummyItem dummy_id = %x>" % (self.dummy_id,)
            
pdus = { 0x01: A_ASSOCIATE_RQ,
         0x02: A_ASSOCIATE_AC,
         0x03: A_ASSOCIATE_RJ,
         0x04: P_DATA_TF,
         0x05: A_RELEASE_RQ,
         0x06: A_RELEASE_RP,
         0x07: A_ABORT,
         0x10: ApplicationContextItem,
         0x20: A_ASSOCIATE_RQ.PresentationContextItem,
         0x21: A_ASSOCIATE_AC.PresentationContextItem,
         0x30: AbstractSyntaxSubitem,
         0x40: TransferSyntaxSubitem,
         0x50: UserInformationItem,
         0x51: MaximumLengthSubitem,
         0x52: ImplementationClassUIDSubitem,
         0x53: AsynchronousOperationsWindowSubitem,
         0x54: SCPSCURoleSelectionSubitem,
         0x55: ImplementationVersionNameSubitem,
         0x56: SOPClassExtendedNegotiationSubitem,
         0x57: SOPClassCommonExtendedNegotiationSubitem,
         0x58: A_ASSOCIATE_RQ.UserIdentitySubitem,
         0x59: A_ASSOCIATE_AC.UserIdentitySubitem,
         0xFF: DummyItem,
         }
