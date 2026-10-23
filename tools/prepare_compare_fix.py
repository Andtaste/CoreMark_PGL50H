"""Isolate explicit-sign comparison fix; preserve production until verified."""
from pathlib import Path
import json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 src=ROOT/'hardware/pds';dest=ROOT/'simulation/results/report_compare_fix83_20261023';assert not dest.exists();dest.mkdir()
 for f in ('source','ipcore','constraints','memory'):shutil.copytree(src/f,dest/f)
 for f in ('boot_interleaved.hex','generate_bitstream.tcl'):shutil.copyfile(src/f,dest/f)
 s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text());(dest/'new_core.pds').write_text(s)
 p=dest/'source/core/nc_execute.v';s=p.read_text()
 needle=' wire[31:0] left_value=a<<rhs[4:0];'
 assert needle in s
 s=s.replace(needle,''' // Explicit sign-bit selection avoids ADS merging signed and unsigned
 // relational expressions into the same signed comparator. The lower31
 // magnitude comparison has no sign ambiguity; branch operands differ
 // from ALU immediates, so retain separate branch and ALU inputs.
 wire alu_low_lt=a[30:0]<rhs[30:0];
 wire alu_signed_lt=(a[31]!=rhs[31]) ? a[31] : alu_low_lt;
 wire alu_unsigned_lt=(a[31]!=rhs[31]) ? rhs[31] : alu_low_lt;
 wire branch_low_lt=a[30:0]<b[30:0];
 wire branch_signed_lt=(a[31]!=b[31]) ? a[31] : branch_low_lt;
 wire branch_unsigned_lt=(a[31]!=b[31]) ? b[31] : branch_low_lt;
'''+needle)
 for a,b in [('$signed(a)<$signed(rhs)','alu_signed_lt'),('a<rhs','alu_unsigned_lt'),('$signed(a)<$signed(b)','branch_signed_lt'),('$signed(a)>=$signed(b)','!branch_signed_lt'),('taken=a<b','taken=branch_unsigned_lt'),('taken=a>=b','taken=!branch_unsigned_lt')]:
  assert a in s,a;s=s.replace(a,b)
 p.write_text(s)
 (dest/'change.json').write_text(json.dumps({'parent':'hardware/pds','change':'Explicit sign-bit split for signed/unsigned ALU and branch comparisons','firmware':'unchanged'},indent=2))
 with (dest/'synthesis.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','synthesize'],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
 print('SYNTHESIZED comparison fix',dest)
if __name__=='__main__':main()
