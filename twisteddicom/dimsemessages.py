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

import tempfile
import dicom
from io import BytesIO
from twisted.python import log
from twisteddicom.utils import get_uid

# See DICOM PS3.7-2011, Table E.1-1
DimseDicomDictionary = {
    0x00000000: ('UL', '1', 'Command Group Length', '', 'CommandGroupLength'),
    0x00000002: ('UI', '1', 'Affected SOP Class UID', '', 'AffectedSOPClassUID'),
    0x00000003: ('UI', '1', 'Requested SOP Class UID', '', 'RequestedSOPClassUID'),
    0x00000100: ('US', '1', 'Command Field', '', 'CommandField'),
    0x00000110: ('US', '1', 'Message ID', '', 'MessageID'),
    0x00000120: ('US', '1', 'Message ID Being Responded To', '', 'MessageIDBeingRespondedTo'),
    0x00000600: ('AE', '1', 'Move Destination', '', 'MoveDestination'),
    0x00000700: ('US', '1', 'Priority', '', 'Priority'),
    0x00000800: ('US', '1', 'Command Data Set Type', '', 'CommandDataSetType'),
    0x00000900: ('US', '1', 'Status', '', 'Status'),
    0x00000901: ('AT', '1-n', 'Offending Element', '', 'OffendingElement'),
    0x00000902: ('LO', '1', 'Error Comment', '', 'ErrorComment'),
    0x00000903: ('US', '1', 'Error ID', '', 'ErrorID'),
    0x00001000: ('UI', '1', 'Affected SOP Instance UID', '', 'AffectedSOPInstanceUID'),
    0x00001001: ('UI', '1', 'Requested SOP Instance UID', '', 'RequestedSOPInstanceUID'),
    0x00001002: ('US', '1', 'Event Type ID', '', 'EventTypeID'),
    0x00001005: ('AT', '1-n', 'Attribute Identifier List', '', 'AttributeIdentifierList'),
    0x00001008: ('US', '1', 'Action Type ID', '', 'ActionTypeID'),
    0x00001020: ('US', '1', 'Number of Remaining Sub-operations', '', 'NumberofRemainingSuboperations'),
    0x00001021: ('US', '1', 'Number of Completed Sub-operations', '', 'NumberofCompletedSuboperations'),
    0x00001022: ('US', '1', 'Number of Failed Sub-operations', '', 'NumberofFailedSuboperations'),
    0x00001023: ('US', '1', 'Number of Warning Sub-operations', '', 'NumberofWarningSuboperations'),
    0x00001030: ('AE', '1', 'Move Originator Application Entity Title', '', 'MoveOriginatorApplicationEntityTitle'),
    0x00001031: ('US', '1', 'Move Originator Message ID', '', 'MoveOriginatorMessageID'),
}

def debuglog(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwds):
        log.msg("Entering %s - %s" % (func.__name__, func.__doc__))
        return func(*args, **kwds)
    return wrapper    

dicom._dicom_dict.DicomDictionary.update(DimseDicomDictionary)

# TODO: Add method update_namedict() to datadict.py
# Provide for the 'reverse' lookup. Given clean name, what is the tag?
dicom.datadict.NameDict = {dicom.datadict.CleanName(tag): tag for tag in dicom.datadict.DicomDictionary}

def is_little_endian(ts):
    if ts == dicom.UID.ExplicitVRBigEndian:
        return False
    else:
        return True

def is_implicit_VR(ts):
    if ts == dicom.UID.ImplicitVRLittleEndian:
        return True
    else:
        return False

def DicomFileBytesIO(is_implicit_VR = True, is_little_endian = True, buf = b''):
    fp = dicom.filebase.DicomFileLike(BytesIO(buf))
    fp.is_implicit_VR = is_implicit_VR
    fp.is_little_endian = is_little_endian
    return fp

def pack_dataset(dicomDataset, is_implicit_VR = True, is_little_endian = True):
    fp = DicomFileBytesIO(is_implicit_VR = is_implicit_VR, is_little_endian = is_little_endian)
    dicom.filewriter.write_dataset(fp, dicomDataset)
    return fp.parent.getvalue()

def unpack_dataset(buf, ts = dicom.UID.ImplicitVRLittleEndian):
    try:
        fp = BytesIO(buf)
        ds = dicom.filereader.read_dataset(fp, is_implicit_VR(ts), is_little_endian(ts), bytelength = len(buf))
        assert ds != None
        return ds
    except Exception, e:
        log.err(e)
        tf = tempfile.NamedTemporaryFile(delete = False)
        log.err("Error decoding dataset with ts %s. Writing to file %s." % (ts, tf.name))
        tf.write(buf)
        tf.close()
        return None

def pack_dataset_with_commandgrouplength(dicomDataset, *args, **kwargs):
    s = pack_dataset(dicomDataset, *args, **kwargs)
    ds2 = dicom.dataset.Dataset()
    ds2.CommandGroupLength = len(s)
    s = pack_dataset(ds2, *args, **kwargs) + s
    return s

def unpack_dimse_command(dataset):
    obj = revcommands[dataset.CommandField]()
    obj.unpack(dataset)
    return obj

class Priority(object):
    LOW = 2
    MEDIUM = 0
    HIGH = 1
    names = ['MEDIUM', 'HIGH', 'LOW']

class DIMSEMessage(object):
    def __repr__(self):
        return ("<%s DIMSE command%s>" 
                % (self.__class__.__name__, "".join(", %s = %s" % (k, dicom.UID.UID_dictionary.get(v, (v,))[0]) 
                                                    for k, v in self.__dict__.iteritems())))

    
class C_STORE_RQ(DIMSEMessage):
    def __init__(self, move_originator_application_entity_title = None, move_originator_message_id = None, 
                 priority = Priority.LOW, message_id = 0, 
                 affected_sop_instance_uid = "", affected_sop_class_uid = ""):
        self.move_originator_message_id = move_originator_message_id
        self.move_originator_application_entity_title = move_originator_application_entity_title
        self.priority = priority
        self.message_id = message_id
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid

    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_STORE_RQ]
        ds.MessageID = self.message_id
        ds.Priority = self.priority
        ds.CommandDataSetType = 0x01
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        if self.move_originator_message_id != None:
            ds.MoveOriginatorMessageID = self.move_originator_message_id
        if self.move_originator_application_entity_title != None:
            ds.MoveOriginatorApplicationEntityTitle = self.move_originator_application_entity_title
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        #assert ds.AffectedSOPClassUID == self.data.SOPClassUID
        self.message_id = ds.MessageID
        self.priority = ds.Priority
        assert ds.CommandField == commands[C_STORE_RQ]
        assert ds.CommandDataSetType != 0x0101
        self.move_originator_application_entity_title = getattr(ds, 'MoveOriginatorApplicationEntityTitle', '')
        self.move_originator_message_id = getattr(ds, 'MoveOriginatorMessageID', '')
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        self.affected_sop_class_uid = ds.AffectedSOPClassUID

class C_STORE_RSP(DIMSEMessage):
    def __init__(self, message_id_being_responded_to = 0, 
                 affected_sop_class_uid = "", affected_sop_instance_uid = "", 
                 status = 0):
        self.message_id_being_responded_to = message_id_being_responded_to
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.status = status
        
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_STORE_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x0101
        ds.Status = self.status # Annex C
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        return pack_dataset_with_commandgrouplength(ds)
        
    def unpack(self, ds):
        assert ds.CommandField == commands[C_STORE_RSP]
        assert ds.CommandDataSetType == 0x0101
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        self.status = ds.Status

class C_GET_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.3.1"""
    def __init__(self, priority = Priority.LOW, message_id = 0, affected_sop_class_uid = ""):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.message_id = message_id
        self.priority = priority
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_GET_RQ]
        ds.MessageID = self.message_id
        ds.Priority = self.priority
        ds.CommandDataSetType = 0x01
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.message_id = ds.MessageID
        self.priority = ds.Priority
        assert ds.CommandField == commands[C_GET_RQ]
        assert ds.CommandDataSetType != 0x0101

class C_GET_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.3.2"""
    def __init__(self, affected_sop_class_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0,
                 number_of_remaining_sub_operations = 0, number_of_completed_sub_operations = 0, 
                 number_of_failed_sub_operations = 0, number_of_warning_sub_operations = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
        self.number_of_remaining_sub_operations = number_of_remaining_sub_operations
        self.number_of_completed_sub_operations = number_of_completed_sub_operations
        self.number_of_failed_sub_operations = number_of_failed_sub_operations
        self.number_of_warning_sub_operations = number_of_warning_sub_operations
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_GET_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        if self.status & 0xFF00 == 0xFF00:
            # Pending must contain number of remaining subitems
            ds.NumberofRemainingSuboperations = self.number_of_remaining_sub_operations
        elif self.status == 0xFE00: # Cancelled
            # may have remaining subops
            ds.NumberofRemainingSuboperations = self.number_of_remaining_sub_operations            
        elif (self.status == 0xA701 or # Failure
            self.status == 0xA702 or # Failure
            self.status == 0xA801 or # Failure
            self.status == 0xA900 or # Failure
            self.status & 0xFF00 == 0xC000 or # Failure
            self.status == 0xB000 or # Warning
            self.status == 0x0000): # Success
            pass # Required _not_ to have remaining subops
        else:
            # Unknown status
            pass
        ds.NumberofCompletedSuboperations = self.number_of_completed_sub_operations
        ds.NumberofFailedSuboperations = self.number_of_failed_sub_operations
        ds.NumberofWarningSuboperations = self.number_of_warning_sub_operations
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        assert ds.CommandField == commands[C_GET_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status
        self.number_of_remaining_sub_operations = ds.NumberofRemainingSuboperations
        self.number_of_completed_sub_operations = ds.NumberofCompletedSuboperations
        self.number_of_failed_sub_operations = ds.NumberofFailedSuboperations
        self.number_of_warning_sub_operations = ds.NumberofWarningSuboperations

class C_FIND_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.2.1"""
    def __init__(self, priority = Priority.LOW, message_id = 0, affected_sop_class_uid = ""):
        self.priority = priority
        self.message_id = message_id
        self.affected_sop_class_uid = affected_sop_class_uid
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[C_FIND_RQ]
        ds.MessageID = self.message_id
        ds.Priority = self.priority
        ds.CommandDataSetType = 0x01
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        self.priority = ds.Priority
        assert ds.CommandField == commands[C_FIND_RQ]
        assert ds.CommandDataSetType != 0x0101
        self.affected_sop_class_uid = ds.AffectedSOPClassUID

class C_FIND_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.2.2"""
    def __init__(self, affected_sop_class_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_FIND_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        assert ds.CommandField == commands[C_FIND_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status
        
class C_MOVE_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.4.1"""
    def __init__(self, priority = Priority.LOW, message_id = 0, affected_sop_class_uid = "", move_destination = ""):
        self.priority = priority
        self.message_id = message_id
        self.affected_sop_class_uid = affected_sop_class_uid
        self.move_destination = move_destination
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_MOVE_RQ]
        ds.MessageID = self.message_id
        ds.Priority = self.priority
        ds.CommandDataSetType = 0x01
        ds.MoveDestination = self.move_destination
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        self.priority = ds.Priority
        assert ds.CommandField == commands[C_MOVE_RQ]
        assert ds.CommandDataSetType != 0x0101
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.move_destination = ds.MoveDestination

class C_MOVE_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.4.2"""
    def __init__(self, affected_sop_class_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0,
                 number_of_remaining_sub_operations = 0, number_of_completed_sub_operations = 0, 
                 number_of_failed_sub_operations = 0, number_of_warning_sub_operations = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
        self.number_of_remaining_sub_operations = number_of_remaining_sub_operations
        self.number_of_completed_sub_operations = number_of_completed_sub_operations
        self.number_of_failed_sub_operations = number_of_failed_sub_operations
        self.number_of_warning_sub_operations = number_of_warning_sub_operations
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.CommandField = commands[C_MOVE_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        ds.NumberofRemainingSuboperations = self.number_of_remaining_sub_operations
        ds.NumberofCompletedSuboperations = self.number_of_completed_sub_operations
        ds.NumberofFailedSuboperations = self.number_of_failed_sub_operations
        ds.NumberofWarningSuboperations = self.number_of_warning_sub_operations
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        assert ds.CommandField == commands[C_MOVE_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status
        self.number_of_remaining_sub_operations = ds.NumberofRemainingSuboperations
        self.number_of_completed_sub_operations = ds.NumberofCompletedSuboperations
        self.number_of_failed_sub_operations = ds.NumberofFailedSuboperations
        self.number_of_warning_sub_operations = ds.NumberofWarningSuboperations

class C_ECHO_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.5.1"""
    def __init__(self, message_id = 0):
        self.message_id = message_id

    def pack(self):
        ds = dicom.dataset.Dataset()
        sop_class_uid = get_uid("Verification SOP Class")
        ds.AffectedSOPClassUID = sop_class_uid
        ds.CommandField = commands[C_ECHO_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x0101
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        assert ds.CommandField == commands[C_ECHO_RQ]
        assert ds.CommandDataSetType == 0x0101
        assert ds.AffectedSOPClassUID == get_uid("Verification SOP Class")
        self.message_id = ds.MessageID

class C_ECHO_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.5.1"""
    def __init__(self, message_id_being_responded_to = 0, status = 0):
        self.message_id_being_responded_to = message_id_being_responded_to
        self.status = status

    def pack(self):
        ds = dicom.dataset.Dataset()
        sop_class_uid = get_uid("Verification SOP Class")
        ds.AffectedSOPClassUID = sop_class_uid
        ds.CommandField = commands[C_ECHO_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        assert ds.CommandField == commands[C_ECHO_RSP]
        assert ds.CommandDataSetType == 0x0101
        assert ds.AffectedSOPClassUID == get_uid("Verification SOP Class")
        self.status = ds.Status
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo

class N_EVENT_REPORT_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.1.1"""
    def __init__(self, affected_sop_class_uid = "", message_id = 0, affected_sop_instance_uid = "", 
                 data_set_present = False, event_type_id = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id = message_id
        self.data_set_present = data_set_present
        assert 0 <= event_type_id < 65536
        self.event_type_id = event_type_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_EVENT_REPORT_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.EventTypeID = self.event_type_id
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_EVENT_REPORT_RQ]
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.event_type_id = ds.EventTypeID

class N_EVENT_REPORT_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.1.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0, event_type_id = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
        self.event_type_id = event_type_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_EVENT_REPORT_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        ds.EventTypeID = self.event_type_id
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_EVENT_REPORT_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status
        self.event_type_id = ds.EventTypeID

class N_GET_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.2.1"""
    def __init__(self, requested_sop_class_uid = "", message_id = 0, requested_sop_instance_uid = ""):
        self.requested_sop_class_uid = requested_sop_class_uid
        self.requested_sop_instance_uid = requested_sop_instance_uid
        self.message_id = message_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_GET_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x0101
        ds.RequestedSOPClassUID = self.requested_sop_class_uid
        ds.RequestedSOPInstanceUID = self.requested_sop_instance_uid
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_GET_RQ]
        assert ds.CommandDataSetType == 0x0101
        self.requested_sop_instance_uid = ds.RequestedSOPInstanceUID
        self.requested_sop_class_uid = ds.RequestedSOPClassUID

class N_GET_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.2.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_GET_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_GET_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status

class N_SET_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.3.1"""
    def __init__(self, requested_sop_class_uid = "", message_id = 0, requested_sop_instance_uid = ""):
        self.requested_sop_class_uid = requested_sop_class_uid
        self.requested_sop_instance_uid = requested_sop_instance_uid
        self.message_id = message_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_SET_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x01
        ds.RequestedSOPClassUID = self.requested_sop_class_uid
        ds.RequestedSOPInstanceUID = self.requested_sop_instance_uid
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_SET_RQ]
        assert ds.CommandDataSetType != 0x0101
        self.requested_sop_instance_uid = ds.RequestedSOPInstanceUID
        self.requested_sop_class_uid = ds.RequestedSOPClassUID

class N_SET_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.3.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_SET_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_SET_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status

class N_ACTION_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.4.1"""
    def __init__(self, requested_sop_class_uid = "", message_id = 0, requested_sop_instance_uid = "", 
                 data_set_present = False, action_type_id = 0):
        self.requested_sop_class_uid = requested_sop_class_uid
        self.requested_sop_instance_uid = requested_sop_instance_uid
        self.message_id = message_id
        self.data_set_present = data_set_present
        assert 0 <= action_type_id < 0xffff
        self.action_type_id = action_type_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_ACTION_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.RequestedSOPClassUID = self.requested_sop_class_uid
        ds.RequestedSOPInstanceUID = self.requested_sop_instance_uid
        ds.ActionTypeID = self.action_type_id
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_ACTION_RQ]
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.requested_sop_instance_uid = ds.RequestedSOPInstanceUID
        self.requested_sop_class_uid = ds.RequestedSOPClassUID
        self.action_type_id = ds.ActionTypeID

class N_ACTION_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.4.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0, action_type_id = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
        self.action_type_id = action_type_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_ACTION_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        ds.ActionTypeID = self.action_type_id
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_ACTION_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status
        self.action_type_id = ds.ActionTypeID

class N_CREATE_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.5.1"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id = 0, 
                 data_set_present = False):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id = message_id
        self.data_set_present = data_set_present
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_CREATE_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_CREATE_RQ]
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        self.affected_sop_class_uid = ds.AffectedSOPClassUID

class N_CREATE_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.5.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 data_set_present = False, status = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.data_set_present = data_set_present
        self.status = status
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_CREATE_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x01 if self.data_set_present else 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_CREATE_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        self.data_set_present = (ds.CommandDataSetType != 0x0101)
        self.status = ds.Status

class N_DELETE_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.6.1"""
    def __init__(self, requested_sop_class_uid = "", message_id = 0, requested_sop_instance_uid = ""):
        self.requested_sop_class_uid = requested_sop_class_uid
        self.requested_sop_instance_uid = requested_sop_instance_uid
        self.message_id = message_id
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[N_DELETE_RQ]
        ds.MessageID = self.message_id
        ds.CommandDataSetType = 0x0101
        ds.RequestedSOPClassUID = self.requested_sop_class_uid
        ds.RequestedSOPInstanceUID = self.requested_sop_instance_uid
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.message_id = ds.MessageID
        assert ds.CommandField == commands[N_DELETE_RQ]
        assert ds.CommandDataSetType == 0x0101
        self.requested_sop_instance_uid = ds.RequestedSOPInstanceUID
        self.requested_sop_class_uid = ds.RequestedSOPClassUID

class N_DELETE_RSP(DIMSEMessage):
    """See DICOM PS3.7-2011 10.3.6.2"""
    def __init__(self, affected_sop_class_uid = "", affected_sop_instance_uid = "", message_id_being_responded_to = 0, 
                 status = 0):
        self.affected_sop_class_uid = affected_sop_class_uid
        self.affected_sop_instance_uid = affected_sop_instance_uid
        self.message_id_being_responded_to = message_id_being_responded_to
        self.status = status
    
    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.AffectedSOPClassUID = self.affected_sop_class_uid
        ds.AffectedSOPInstanceUID = self.affected_sop_instance_uid
        ds.CommandField = commands[N_DELETE_RSP]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x0101
        ds.Status = self.status
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        self.affected_sop_class_uid = ds.AffectedSOPClassUID
        self.affected_sop_instance_uid = ds.AffectedSOPInstanceUID
        assert ds.CommandField == commands[N_DELETE_RSP]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        assert ds.CommandDataSetType == 0x0101
        self.status = ds.Status

class C_CANCEL_RQ(DIMSEMessage):
    """See DICOM PS3.7-2011 9.3.5.1"""
    def __init__(self, message_id_being_responded_to = 0):
        self.message_id_being_responded_to = message_id_being_responded_to

    def pack(self):
        ds = dicom.dataset.Dataset()
        ds.CommandField = commands[C_CANCEL_RQ]
        ds.MessageIDBeingRespondedTo = self.message_id_being_responded_to
        ds.CommandDataSetType = 0x0101
        return pack_dataset_with_commandgrouplength(ds)

    def unpack(self, ds):
        assert ds.CommandField == commands[C_CANCEL_RQ]
        self.message_id_being_responded_to = ds.MessageIDBeingRespondedTo
        assert ds.CommandDataSetType == 0x0101

# See DICOM PS3.7-2011, Table E.1-1, Description of Field "Command Field"
commands = {
    C_STORE_RQ: 0x0001,
    C_STORE_RSP: 0x8001,
    C_GET_RQ: 0x0010,
    C_GET_RSP: 0x8010,
    C_FIND_RQ: 0x0020,
    C_FIND_RSP: 0x8020,
    C_MOVE_RQ: 0x0021,
    C_MOVE_RSP: 0x8021,
    C_ECHO_RQ: 0x0030,
    C_ECHO_RSP: 0x8030,
    N_EVENT_REPORT_RQ: 0x0100,
    N_EVENT_REPORT_RSP: 0x8100,
    N_GET_RQ: 0x0110,
    N_GET_RSP: 0x8110,
    N_SET_RQ: 0x0120,
    N_SET_RSP: 0x8120,
    N_ACTION_RQ: 0x0130,
    N_ACTION_RSP: 0x8130,
    N_CREATE_RQ: 0x8140,
    N_CREATE_RSP: 0x0140,
    N_DELETE_RQ: 0x0150,
    N_DELETE_RSP: 0x8150,
    C_CANCEL_RQ: 0x0FFF, 
}

# Reverse commands list
revcommands = {v:k for k,v in commands.iteritems()}
