"""Validate dedicated AGU and published registered-write address contracts."""
from pathlib import Path
import sys,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_launch';base=ROOT/'tools/check_dual_boundary_memory.py';s=base.read_text().replace("reads=int(a.variant.endswith('_read'))",'reads=1').replace('.packet(packet),.side_packet','.packet(packet),.launch_address(packet[148:117]),.write_address(),.side_packet')
 ns={'__file__':str(base),'__name__':'launch_memory'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant','dual_boundary_launch'];ns['main']();p=src/'memory_checks/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n')
 out=src/'address_contract';out.mkdir(exist_ok=True);original=src/'checks/core_tb.v';tb=out/'core_tb.v'
 mon='''
 integer addr_load=0,addr_store=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.d_write && (!dut.d_req_valid || dut.d_write_addr!==dut.d_addr)) $fatal(1,"Published write qualification/address mismatch");
  if(dut.memory.early_request && dut.launch_address!==dut.mem_packet[148:117]) $fatal(1,"Dedicated load AGU differs from architectural packet address");
  if(dut.memory.early_request && dut.d_req_ready) addr_load=addr_load+1;
  if(dut.d_write && dut.d_req_ready) addr_store=addr_store+1;
 end
 always @(negedge clk) if(finish_count==1) $display("ADDRESS_CONTRACT load=%0d store=%0d",addr_load,addr_store);
''';tb.write_text(original.read_text().replace('endmodule',mon+'\nendmodule'));g=json.loads((src/'generation.json').read_text());files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v'))];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[Path(__file__).resolve(),original,tb,*files];tests=[]
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-2000:];return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','core_tb','-o',out/'sim.vvp',*files,tb],'compile.log')
 for name in ('random_17','random_91','random_2026','prediction','directed'):
  image=ROOT/('simulation/results/'+name+'.hex');inputs.append(image)
  for seed in (37,613):
   t=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={out}/{name}_{seed}.trace',f'+seed={seed}'],f'{name}_{seed}.log');assert 'PASS cycles=' in t and 'ADDRESS_CONTRACT' in t,t[-2000:];tests.append(f'PASS {name} seed={seed} dedicated-address and published-write invariant')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('launch address contract PASS')
if __name__=='__main__':main()
