"""Small regression tests for payloads Git diff does not expose as text."""
from base64 import b64encode
import gzip
from io import BytesIO
import json
import struct
import unittest
from zipfile import ZipFile

from audit_public_history import Audit


class PublicAuditTest(unittest.TestCase):
    def test_nested_viewer_credential_is_detected_without_printing_value(self):
        value="gh"+"p_"+"a"*36
        payload=json.dumps({"asset":{"version":"2.0","extras":{"old_token":value}}}).encode()
        payload+=b" "*(-len(payload)%4)
        model=struct.pack("<4sIIII",b"glTF",2,20+len(payload),len(payload),0x4e4f534a)+payload
        html=b'<script id="model-bytes">'+b64encode(gzip.compress(model))+b"</script>"
        buf=BytesIO()
        with ZipFile(buf,"w") as z:z.writestr("viewer.html",html)
        audit=Audit();audit.blob("candidate.zip",buf.getvalue())
        self.assertTrue(any(category=="credential-shaped value" for _,category in audit.findings))
        self.assertNotIn(value,str(audit.findings))

    def test_archive_is_not_silently_skipped(self):
        audit=Audit();audit.blob("art.sc",b"broken")
        self.assertTrue(audit.findings)

    def test_public_provenance_link_is_not_a_credential(self):
        audit=Audit();audit.blob("credit.md",b"See https://github.com/example/kit/ and https://www.printables.com/")
        self.assertFalse(audit.findings)


if __name__=="__main__":
    unittest.main()
