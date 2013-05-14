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
import datetime
import re
from twisted.python import log

do_log = False

def get_uid(name):
    candidates = [k for k,v in dicom._UID_dict.UID_dictionary.iteritems() if v[0] == name]
    assert len(candidates) == 1
    return candidates[0]

def generate_uid(_uuid = None):
    """Returns a new DICOM UID based on a UUID, as specified in CP1156 (Final)."""
    if _uuid == None:
        _uuid = uuid.uuid1()
    return "2.25.%i" % _uuid.int

import uuid

class UTCOffsetTimeZone(datetime.tzinfo):
    def __init__(self, s):
        assert len(s) == 5
        assert s[0] == "+" or s[0] == "-"
        if s[0] == "+":
            sign = 1
        else:
            sign = -1
        self.tzdelta = datetime.timedelta(hours=sign*int(s[1:3]), minutes = sign*int(s[3:5]))
    def utcoffset(self, dt):
        return self.tzdelta
    def dst(self, dt):
        return datetime.timedelta(0)

def parse_da_dt_tm(s, vr):
    if vr == "DA":
        return datetime.date.fromordinal(datetime.datetime.strptime(s, "%Y%m%d").toordinal())
    elif vr == "TM":
        if len(s) == 6:
            return datetime.time(int(s[:2]), int(s[2:4]), int(s[4:6]))
        elif 8 <= len(s) <= 8+6:
            return datetime.time(int(s[:2]), int(s[2:4]), int(s[4:6]), int(s[7:]))
        else:
            raise ValueError("\"%s\" is not a valid DICOM time" % (s,))
    elif vr == "DT":
        if len(s) == 8:
            return datetime.datetime.strptime(s, "%Y%m%d")
        elif len(s) == 8+4:
            return datetime.datetime.strptime(s, "%Y%m%d%H%M")
        elif len(s) == 8+6:
            return datetime.datetime.strptime(s, "%Y%m%d%H%M%S")
        elif 8+8 <= len(s) <= 8+8+6 and s.find("+") == -1 and s.find("-") == -1:
            return datetime.datetime(int(s[:4]), int(s[4:6]), int(s[6:8]), 
                                     int(s[8:10]), int(s[10:12]), int(s[12:14]), int(s[15:]))
        elif 8+8+5 <= len(s) <= 8+8+6+5 and (s.find("+") != -1 or s.find("-") != -1):
            i = s.find("-")
            if i == -1:
                i = s.find("+")
            return datetime.datetime(int(s[:4]), int(s[4:6]), int(s[6:8]), 
                                     int(s[8:10]), int(s[10:12]), int(s[12:14]), int(s[15:i]), 
                                     UTCOffsetTimeZone(s[i:]))

def attribute_match(pattern, value, vr):
    """See PS 3.4 C.2.2.2."""
    if do_log: log.msg("attribute_match(%s, %s, %s)" % (pattern, value, vr))
    if pattern == "*" or pattern == "":
        return True
    if (vr == "DT" or vr == "TM" or vr == "DA"):
        value = parse_da_dt_tm(value, vr)
        if pattern.startswith("-"):
            maxvalue = parse_da_dt_tm(pattern[1:], vr)
            return value <= maxvalue
        elif pattern.endswith("-"):
            minvalue = parse_da_dt_tm(pattern[1:], vr)
            return value >= minvalue
        elif pattern.find("-") != -1:
            # TODO: This is broken for DT with negative time zone offsets. FIXME!
            minvalue, maxvalue = [parse_da_dt_tm(x, vr) for x in pattern.split("-")]
            return minvalue <= value <= maxvalue
        else:
            pattern = parse_da_dt_tm(pattern, vr)
            return value == pattern
    if re.match(str(pattern).replace("*", ".*"), str(value)):
        return True
    return False

def match_dataset(query, ds):
    result_ds = dicom.dataset.Dataset()
    for key in query.iterkeys():
        if key == 0x00080052: # Query/Retrieve Level
            continue 
        if key & 0x0000ffff == 0: # Group Length
            continue
        if key == 0x00080005: # Specific Character set
            continue
        if query[key].VR == "SQ":
            if do_updates and len(query[key].value) == 0:
                if key in ds:
                    result_ds[key] = ds[key]
                else:
                    result_ds[key] = query[key]
                continue
            sub_results = []
            for item in ds[key].value:
                if key & 0x0000ffff == 0: # Group Length
                    continue
                is_match, sub_result_ds = match_dataset(query[key].value[0], item, do_updates = do_updates)
                if not is_match: 
                    continue
                sub_results.append(sub_result_ds)
            if len(sub_results) == 0 and len(ds[key].value) != 0:
                if do_log: log.msg("failed match due to key %s (no matches in sequence)" % (key,))
                return False, None
            result_ds[key] = dicom.dataelem.DataElement(key, query[key].VR, dicom.sequence.Sequence(sub_results))
        elif key not in ds:
            if query[key].value == None or query[key].value == '': # universal matcher
                result_ds[key] = query[key]
            else:
                if do_log: log.msg("failed match due to key %s (not present)" % (key,))
                return False, None
        elif not attribute_match(query[key].value, ds[key].value, query[key].VR):
            if do_log: log.msg("failed match due to key %s (%s != %s)" % (key, query[key].value, ds[key].value))
            return False, None
        else:
            result_ds[key] = ds[key]
    return True, result_ds

def get_level_identifier(ds, level):
    if level == "IMAGE":
        return getattr(ds, "SOPInstanceUID", None)
    elif level == "SERIES":
        return getattr(ds, "SeriesInstanceUID", None)
    elif level == "STUDY":
        return getattr(ds, "StudyInstanceUID", None)
    elif level == "PATIENT":
        return getattr(ds, "PatientID", None)
    else:
        raise ValueError("Unknown query/retrieve level \"%s\"!" % level)

def write_ds(ds, fn, default_sopclass=None):
    ds.file_meta = dicom.dataset.Dataset()
    ds.file_meta.TransferSyntaxUID = dicom.UID.ImplicitVRLittleEndian
    if default_sopclass == None:
        default_sopclass = get_uid("Study Root Query/Retrieve Information Model - FIND")
    ds.file_meta.MediaStorageSOPClassUID = getattr(ds, 'SOPClassUID', default_sopclass)
    ds.file_meta.MediaStorageSOPInstanceUID = getattr(ds, 'SOPInstanceUID', generate_uid())
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    ds.file_meta.ImplementationClassUID = '2.25.4282708245307149051252828097685724107'
    dicom.write_file(fn, ds, WriteLikeOriginal=False)

def update_dataset(ds, changes):
    for key in changes.iterkeys():
        if key & 0x0000ffff == 0: # Group Length
            continue
        if key == 0x00080018 or key == 0x00080016: # SOP (Class | Instance) UID
            continue
        ds[key] = changes[key]
