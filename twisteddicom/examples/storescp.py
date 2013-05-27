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
from twisted.python import log
from twisteddicom.utils import generate_uid

supported_abstract_syntaxes = [
    '1.2.840.10008.1.1', # Verification SOP Class
#    '1.2.840.10008.1.3.10', # Media Storage Directory Storage
    '1.2.840.10008.5.1.4.1.1.1', # Computed Radiography Image Storage
    '1.2.840.10008.5.1.4.1.1.2', # CT Image Storage
    '1.2.840.10008.5.1.4.1.1.2.1', # Enhanced CT Image Storage
    '1.2.840.10008.5.1.4.1.1.3', # Ultrasound Multi-frame Image Storage
    '1.2.840.10008.5.1.4.1.1.3.1', # Ultrasound Multi-frame Image Storage
    '1.2.840.10008.5.1.4.1.1.4', # MR Image Storage
    '1.2.840.10008.5.1.4.1.1.4.1', # Enhanced MR Image Storage
    '1.2.840.10008.5.1.4.1.1.4.2', # MR Spectroscopy Storage
    '1.2.840.10008.5.1.4.1.1.5', # Nuclear Medicine Image  Storage
    '1.2.840.10008.5.1.4.1.1.6', # Ultrasound Image Storage
    '1.2.840.10008.5.1.4.1.1.6.1', # Ultrasound Image Storage
    '1.2.840.10008.5.1.4.1.1.6.2', # Enhanced US Volume Storage
    '1.2.840.10008.5.1.4.1.1.7', # Secondary Capture Image Storage
    '1.2.840.10008.5.1.4.1.1.7.1', # Multi-frame Single Bit Secondary Capture Image Storage
    '1.2.840.10008.5.1.4.1.1.7.2', # Multi-frame Grayscale Byte Secondary Capture Image Storage
    '1.2.840.10008.5.1.4.1.1.7.3', # Multi-frame Grayscale Word Secondary Capture Image Storage
    '1.2.840.10008.5.1.4.1.1.7.4', # Multi-frame True Color Secondary Capture Image Storage
    '1.2.840.10008.5.1.4.1.1.8', # Standalone Overlay Storage
    '1.2.840.10008.5.1.4.1.1.9', # Standalone Curve Storage
    '1.2.840.10008.5.1.4.1.1.9.1.1', # 12-lead ECG Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.1.2', # General ECG Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.1.3', # Ambulatory ECG Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.2.1', # Hemodynamic Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.3.1', # Cardiac Electrophysiology Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.4.1', # Basic Voice Audio Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.4.2', # General Audio Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.5.1', # Arterial Pulse Waveform Storage
    '1.2.840.10008.5.1.4.1.1.9.6.1', # Respiratory Waveform Storage
    '1.2.840.10008.5.1.4.1.1.10', # Standalone Modality LUT Storage
    '1.2.840.10008.5.1.4.1.1.11', # Standalone VOI LUT Storage
    '1.2.840.10008.5.1.4.1.1.12.1', # X-Ray Angiographic Image Storage
    '1.2.840.10008.5.1.4.1.1.12.1.1', # Enhanced XA Image Storage
    '1.2.840.10008.5.1.4.1.1.12.2', # X-Ray Radiofluoroscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.12.2.1', # Enhanced XRF Image Storage
    '1.2.840.10008.5.1.4.1.1.13.1.1', # X-Ray 3D Angiographic Image Storage
    '1.2.840.10008.5.1.4.1.1.13.1.2', # X-Ray 3D Craniofacial Image Storage
    '1.2.840.10008.5.1.4.1.1.12.3', # X-Ray Angiographic Bi-Plane Image Storage
    '1.2.840.10008.5.1.4.1.1.20', # Nuclear Medicine Image Storage
    '1.2.840.10008.5.1.4.1.1.66', # Raw Data Storage
    '1.2.840.10008.5.1.4.1.1.66.1', # Spatial Registration Storage
    '1.2.840.10008.5.1.4.1.1.66.2', # Spatial Fiducials Storage
    '1.2.840.10008.5.1.4.1.1.66.3', # Deformable Spatial Registration Storage
    '1.2.840.10008.5.1.4.1.1.66.4', # Segmentation Storage
    '1.2.840.10008.5.1.4.1.1.67', # Real World Value Mapping Storage
    '1.2.840.10008.5.1.4.1.1.77.1.1', # VL Endoscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.1.1', # Video Endoscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.2', # VL Microscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.2.1', # Video Microscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.3', # VL Slide-Coordinates Microscopic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.4', # VL Photographic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.4.1', # Video Photographic Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.5.1', # Ophthalmic Photography 8 Bit Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.5.2', # Ophthalmic Photography 16 Bit Image Storage
    '1.2.840.10008.5.1.4.1.1.77.1.5.3', # Stereometric Relationship Storage
    '1.2.840.10008.5.1.4.1.1.77.1.5.4', # Ophthalmic Tomography Image Storage
    '1.2.840.10008.5.1.4.1.1.88.11', # Basic Text SR Storage
    '1.2.840.10008.5.1.4.1.1.88.22', # Enhanced SR Storage
    '1.2.840.10008.5.1.4.1.1.88.33', # Comprehensive SR Storage
    '1.2.840.10008.5.1.4.1.1.88.40', # Procedure Log Storage
    '1.2.840.10008.5.1.4.1.1.88.50', # Mammography CAD SR Storage
    '1.2.840.10008.5.1.4.1.1.88.59', # Key Object Selection Document Storage
    '1.2.840.10008.5.1.4.1.1.88.65', # Chest CAD SR Storage
    '1.2.840.10008.5.1.4.1.1.88.67', # X-Ray Radiation Dose SR Storage
    '1.2.840.10008.5.1.4.1.1.104.1', # Encapsulated PDF Storage
    '1.2.840.10008.5.1.4.1.1.104.2', # Encapsulated CDA Storage
    '1.2.840.10008.5.1.4.1.1.128', # Positron Emission Tomography Image Storage
    '1.2.840.10008.5.1.4.1.1.129', # Standalone PET Curve Storage
    '1.2.840.10008.5.1.4.1.1.130', # Enhanced PET Image Storage
    '1.2.840.10008.5.1.4.1.1.481.1', # RT Image Storage
    '1.2.840.10008.5.1.4.1.1.481.2', # RT Dose Storage
    '1.2.840.10008.5.1.4.1.1.481.3', # RT Structure Set Storage
    '1.2.840.10008.5.1.4.1.1.481.4', # RT Beams Treatment Record Storage
    '1.2.840.10008.5.1.4.1.1.481.5', # RT Plan Storage
    '1.2.840.10008.5.1.4.1.1.481.6', # RT Brachy Treatment Record Storage
    '1.2.840.10008.5.1.4.1.1.481.7', # RT Treatment Summary Record Storage
    '1.2.840.10008.5.1.4.1.1.481.8', # RT Ion Plan Storage
    '1.2.840.10008.5.1.4.1.1.481.9', # RT Ion Beams Treatment Record Storage
    '1.2.840.10008.5.1.4.38.1', # Hanging Protocol Storage
    ]

class StoreSCP(dimse.DIMSEProtocol):
    def __init__(self):
        super(StoreSCP, self).__init__(supported_abstract_syntaxes = supported_abstract_syntaxes)

    def C_ECHO_RQ_received(self, presentation_context_id, echo_rq, dimse_data):
        log.msg("received DIMSE command %s on presentation context %i" % (echo_rq, presentation_context_id))
        assert echo_rq.__class__ == dimsemessages.C_ECHO_RQ
        log.msg("replying")
        self.send_DIMSE_command(presentation_context_id, dimsemessages.C_ECHO_RSP(echo_rq.message_id))

    def C_STORE_RQ_received(self, presentation_context_id, store_rq, dimse_data):
        log.msg("received DIMSE command %s" % store_rq)
        assert store_rq.__class__ == dimsemessages.C_STORE_RQ
        log.msg("replying to %s" % store_rq)
        status = 0
        try:
            dimse_data.file_meta = dicom.dataset.Dataset()
            dimse_data.file_meta.TransferSyntaxUID = dicom.UID.ImplicitVRLittleEndian
            dimse_data.file_meta.MediaStorageSOPClassUID = dimse_data.SOPClassUID
            dimse_data.file_meta.MediaStorageSOPInstanceUID = generate_uid()
            dimse_data.is_little_endian = True
            dimse_data.is_implicit_VR = True
            dimse_data.file_meta.ImplementationClassUID = '2.25.4282708245307149051252828097685724107'
            dicom.write_file("%s_%s.dcm" % (getattr(dimse_data, 'Modality', 'XX'), dimse_data.SOPInstanceUID), dimse_data, WriteLikeOriginal=False)
        except Exception, e:
            log.err(e)
            status = 1
        rsp = dimsemessages.C_STORE_RSP(message_id_being_responded_to = store_rq.message_id,
                                        affected_sop_class_uid = store_rq.affected_sop_class_uid,
                                        affected_sop_instance_uid = store_rq.affected_sop_instance_uid, 
                                        status=status)
        self.send_DIMSE_command(presentation_context_id, rsp)


from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint

class StoreSCPFactory(Factory, object):
    def __init__(self):
        super(StoreSCPFactory, self).__init__()
    def buildProtocol(self, addr):
        protocol = StoreSCP()
        return protocol

def gotProtocol(p):
    log.msg("hej")
    pass
        
if __name__== '__main__':
    import sys
    log.startLogging(sys.stdout)
    if len(sys.argv) != 2:
        log.msg("Syntax: %s <port>" % sys.argv[0])
        sys.exit(1)
    endpoint = TCP4ServerEndpoint(reactor, port = int(sys.argv[1]))
    endpoint.listen(StoreSCPFactory())
    reactor.run()
    log.msg("reactor.run() exited")
