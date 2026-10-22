"""Prove range classification and adapt existing response/SoC contracts."""
from pathlib import Path
import hashlib,json,argparse,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
LOCAL="(packet[148:117]<32'h00010000 || (packet[148:117]>=32'h10000000 && packet[148:117]<32'h10008000))"
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('proof','module','contracts','soc','uart'),required=True);a=ap.parse_args();src=ROOT/'simulation/results/load_bp_dual_boundary_storeprefix'
 if a.mode=='proof':
  out=src/'range_proof';out.mkdir(exist_ok=True);actual=src/'nc_core.v';decoder=ROOT/'hardware/pds/source/core/nc_decode.v';fun=actual.read_text().split(' function local_load_address;',1)[1].split(' endfunction',1)[0]
  p=out/'range_proof.v';p.write_text('module range_proof(input[31:0] base,insn,output equal);\n function local_load_address;'+fun+' endfunction\n'+'''wire[3:0] kind;wire[31:0] imm;wire[31:0] address=base+imm;
 nc_decode d(.insn(insn),.kind(kind),.imm(imm),.use1(),.use2(),.write_rd(),.serial(),.illegal(),.control(),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));
 wire reference_local=address<32'h00010000 || (address>=32'h10000000 && address<32'h10008000);
 assign equal=kind!=4 || local_load_address(base,imm[11:0])==reference_local;
 endmodule
''')
  def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
  x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(decoder)} {linux(p)}; prep -top range_proof -flatten; sat -verify -prove equal 1'],cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,(x.stdout+x.stderr)[-2000:]
  inputs=[Path(__file__).resolve(),actual,decoder,p];(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['PASS SAT: actual decoder load kind, all32-bit bases/all instruction words including signed offsets and modular wrap; parallel qualifier equals full32-bit range comparisons'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('range SAT PASS');return
 if a.mode=='module':
  base=ROOT/'tools/check_dual_store_ack.py';s=base.read_text().replace('.launch_address(packet[148:117]),.write_address()', '.launch_address(packet[148:117]),.launch_local('+LOCAL+'),.write_address()');sys.argv=[str(base),'--variant','dual_boundary_storeprefix','--mode','module'];sub='posted_module'
 elif a.mode=='contracts':
  base=ROOT/'tools/check_dual_boundary_launch.py';s=base.read_text().replace('dual_boundary_launch','dual_boundary_storeprefix').replace('.launch_address(packet[148:117]),.write_address()', '.launch_address(packet[148:117]),.launch_local('+LOCAL+'),.write_address()')
  s=s.replace(' integer addr_load=0,addr_store=0;', ' integer addr_load=0,addr_store=0;').replace('  if(dut.memory.early_request && dut.launch_address!==dut.mem_packet[148:117])', '  if(dut.memory.early_request && !dut.launch_local) $fatal(1,"Missing early local qualifier");\n  if(dut.memory.early_request && dut.launch_address!==dut.mem_packet[148:117])');sys.argv=[str(base)];sub='address_contract'
 elif a.mode=='soc':
  base=ROOT/'tools/check_dual_store_mmio_v2.py';s=base.read_text().replace('dual_boundary_storemmio','dual_boundary_storeprefix');sys.argv=[str(base)];sub='posted_soc_final'
 else:
  base=ROOT/'tools/check_dual_timing80_uart.py';s=base.read_text().replace('dual_boundary_pair','dual_boundary_storeprefix');sys.argv=[str(base)];sub='uart80'
 ns={'__file__':str(base),'__name__':'prefix_'+a.mode};exec(compile(s,str(base),'exec'),ns);ns['main']()
 for sub in ([sub,'memory_checks'] if a.mode=='contracts' else [sub]):
  p=src/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
