import unittest,sys,tempfile,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"source"))
from spacetag import parse_filename,wav_read,wav_write,write_tags
class BasicTests(unittest.TestCase):
 def test_parse(self):
  self.assertEqual(parse_filename("otr032 Apex - dancer.wav"),{"Catalogue":"OTR032","Artist":"Apex","Title":"dancer"})
 def test_wav_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"OTR032 Apex - dancer.wav"
   audio=b"\x01\x02\x03\x04"
   fmt=struct.pack("<HHIIHH",1,1,44100,88200,2,16)
   body=b"WAVE"+b"fmt "+struct.pack("<I",16)+fmt+b"data"+struct.pack("<I",len(audio))+audio
   p.write_bytes(b"RIFF"+struct.pack("<I",len(body))+body)
   before=p.read_bytes()
   write_tags(p,{"Title":"dancer","Artist":"Apex","Catalogue":"OTR032"})
   after=p.read_bytes()
   self.assertIn(b"data"+struct.pack("<I",4)+audio,after)
   self.assertEqual(wav_read(p)["Catalogue"],"OTR032")
   self.assertEqual(p.name,"OTR032 Apex - dancer.wav")
   self.assertTrue(Path(str(p)+".spacetag.bak").exists())
if __name__=="__main__":unittest.main()
