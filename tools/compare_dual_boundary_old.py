"""Run frozen Round50 CPU and new CPUs on identical firmware/RAM service."""
from pathlib import Path
import argparse,json,hashlib,shutil,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--target',choices=('old','fifo','slot','early'),required=True);a=ap.parse_args();out=ROOT/'simulation/results/dual_boundary_common'/a.target;out.mkdir(parents=True,exist_ok=True)
 old=ROOT.parent/'tmp/dual_round50_20261019/after';inputs=[Path(__file__).resolve()];corefiles=[]
 if a.target=='old':
  hashes=json.loads((old/'source_hashes.json').read_text());snap=out/'core';snap.mkdir(exist_ok=True)
  for p in sorted((old/'source/core').glob('*.v')):
   assert sha(p)==hashes['core/'+p.name],p
   q=snap/p.name;shutil.copyfile(p,q);corefiles.append(q);inputs +=[p,q]
  cp='''tinyriscv_core cpu(.clk(clk),.rst_n(rst_n),.jtag_halt_i(1'b0),.int_i(8'b0),
 .ibus_addr_o(ia),.ibus_data_i(idata),.ibus_req_valid_o(iv),.ibus_req_ready_i(ir),.ibus_rsp_valid_i(iov),.ibus_rsp_ready_o(ior),.ibus_data_o(),.ibus_sel_o(),.ibus_we_o(),
 .dbus_addr_o(da),.dbus_data_i(ddata),.dbus_data_o(dw),.dbus_sel_o(dm),.dbus_we_o(dwrite),.dbus_req_valid_o(dv),.dbus_req_ready_i(dr),.dbus_rsp_valid_i(dov),.dbus_rsp_ready_o(dor),
 .dbus2_addr_o(sa),.dbus2_data_o(sw),.dbus2_data_i(sdata),.dbus2_sel_o(sm),.dbus2_we_o(swrite),.dbus2_req_valid_o(sv),.dbus2_req_ready_i(sr),.dbus2_rsp_valid_i(sov),.dbus2_rsp_ready_o(sor),.dbus_pair_o());
 wire control=cpu.u_csr_reg.stat_control_write,enabled=cpu.u_csr_reg.stat_enable;wire[31:0] control_data=cpu.u_csr_reg.exu_wdata_i;
 wire retire=cpu.wb_commit,retire1=retire && cpu.wb2_valid;wire[31:0] pc0=cpu.wb_pc,pc1=cpu.wb_pc+4;
 wire[31:0] hw_cycles=cpu.u_csr_reg.stat_count[0],hw_retired=cpu.u_csr_reg.stat_count[7],hw_side=cpu.u_csr_reg.stat_secondary_count;
 wire bad=cpu.wb_valid && cpu.wb_exception;
 wire early_direct=cpu.ex_local_request && dv && dr;
'''
 else:
  name='dual_legacy_fifo' if a.target=='fifo' else 'dual_boundary_'+a.target;src=ROOT/('simulation/results/load_bp_'+name);g=json.loads((src/'generation.json').read_text())
  for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v')):corefiles.append(src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p)
  cp='''nc_core cpu(.clk(clk),.rst_n(rst_n),.irq_soft(1'b0),.irq_timer(1'b0),.irq_ext(1'b0),
 .i_req_valid(iv),.i_req_ready(ir),.i_addr(ia),.i_rsp_valid(iov),.i_rsp_ready(ior),.i_data(idata),.i_error(ie),
 .d_req_valid(dv),.d_req_ready(dr),.d_addr(da),.d_wdata(dw),.d_mask(dm),.d_write(dwrite),.d_rsp_valid(dov),.d_rsp_ready(dor),.d_rdata(ddata),.d_error(de),
 .trace_valid(),.trace_trap(),.trace_pc(),.trace_insn(),.trace_data(),.trace_cause(),.trace_rd());
 assign sv=0;assign sa=0;assign sw=0;assign sm=0;assign swrite=0;assign sor=1;
 wire control=cpu.csr.stats.control,enabled=cpu.csr.stats.enabled;wire[31:0] control_data=cpu.csr.stats.control_data;
 wire retire=cpu.commit,retire1=cpu.commit1;wire[31:0] pc0=cpu.w_pc,pc1=cpu.w1_pc;
 wire[31:0] hw_cycles=cpu.csr.stats.counters[1],hw_retired=cpu.csr.stats.counters[9],hw_side=cpu.csr.stats.counters[10];
 wire bad=cpu.do_trap;
 wire early_direct=EARLY;
'''.replace('EARLY',"cpu.memory.early_request && dr && !cpu.queued_valid" if a.target=='early' else "1'b0")
 bus=ROOT/'simulation/results/load_bp_dual_lsu_ports/nc_local_bus.v';model=ROOT/'simulation/results/load_bp_dual_lsu_ports/pango_ram_wide_models.v';uart=out/'nc_uart_sim.v';uart_source=ROOT/'hardware/pds/source/perips/nc_uart.v';uart.write_text(uart_source.read_text().replace('BAUD=115200','BAUD=9375000'))
 tb=out/'common_tb.v';tb.write_text('''`timescale 1ns/1ps
module common_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 wire iv,ir,iov,ior,ie,dv,dr,dov,dor,de,dwrite,sv,sr,sov,sor,swrite,tx;
 wire[63:0] idata;wire[31:0] ia,da,dw,ddata,sa,sw,sdata,tohost;wire[3:0] dm,sm;
 CPU
 nc_local_bus #(.SECOND_PORT(1)) bus(.clk(clk),.rst_n(rst_n),.iv(iv),.ir(ir),.ia(ia),.iov(iov),.ior(ior),.idata(idata),.ierr(ie),
 .dv(dv),.dr(dr),.da(da),.dw(dw),.dm(dm),.dwrite(dwrite),.dov(dov),.dor(dor),.ddata(ddata),.derr(de),
 .sv(sv),.sr(sr),.sa(sa),.sw(sw),.sm(sm),.swrite(swrite),.sov(sov),.sor(sor),.sdata(sdata),.uart_tx(tx),.timer_irq(),.gpio_out(),.tohost(tohost));
 integer ticks=0,cycles=0,retired=0,side=0,early=0,stops=0,finish_count=0;reg check=0;
 reg[63:0] pc_hash=64'hcbf29ce484222325;
 reg[4095:0] uartfile;integer uart_fd,k;reg[7:0] ch;
 initial begin if(!$value$plusargs("uart=%s",uartfile)) $fatal;uart_fd=$fopen(uartfile,"wb");repeat(5) @(negedge clk);rst_n=1;end
 initial forever begin @(negedge tx);if(rst_n) begin repeat(4) @(posedge clk);
 for(k=0;k<8;k=k+1) begin repeat(8) @(posedge clk);ch[k]=tx;end
 repeat(8) @(posedge clk);if(tx!==1) $fatal(1,"UART stop");$fwrite(uart_fd,"%c",ch);$fflush(uart_fd);end end
 always @(posedge clk) if(rst_n) begin
  ticks=ticks+1;check=0;if(ticks>20000000) $fatal(1,"TIMEOUT PC=%h",pc0);
  if(bad) $fatal(1,"Unexpected architectural trap at %h",pc0);
  if(control) begin
   if(control_data[1]) begin cycles=0;retired=0;side=0;early=0;pc_hash=64'hcbf29ce484222325;end
   else if(!control_data[0]) begin check=1;stops=stops+1;end
  end else if(enabled) begin
   cycles=cycles+1;
   if(retire) begin retired=retired+1;pc_hash=(pc_hash^{32'b0,pc0})*64'h100000001b3;end
   if(retire1) begin retired=retired+1;side=side+1;pc_hash=(pc_hash^{32'b0,pc1})*64'h100000001b3;end
   if(early_direct) early=early+1;
  end
  if(tohost!=0 && finish_count==0) begin if(tohost!=1) $fatal(1,"Software fail %h",tohost);finish_count=20;end
  if(finish_count!=0) begin finish_count=finish_count-1;if(finish_count==0) begin if(stops!=1) $fatal(1,"Window missing");$display("COMMON_PASS");$fclose(uart_fd);$finish;end end
 end
 always @(negedge clk) if(check) begin
  if(hw_cycles!=cycles || hw_retired!=retired || hw_side!=side) $fatal(1,"Independent count mismatch %d/%d %d/%d %d/%d",hw_cycles,cycles,hw_retired,retired,hw_side,side);
  $display("COMMON_WINDOW cycles=%0d retired=%0d side=%0d early_direct=%0d pc_hash=%016h",cycles,retired,side,early,pc_hash);
 end
endmodule
'''.replace('CPU',cp))
 inputs +=corefiles+[bus,model,uart_source,uart,tb];prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
 cmd=[*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','common_tb','--Mdir',linux(out/'obj')]
 if a.target=='old':cmd+=['-I'+linux(out/'core')]
 cmd +=[linux(p) for p in corefiles+[bus,model,uart,tb]]
 with (out/'compile.log').open('wb') as f:p=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert p.returncode==0,(out/'compile.log').read_text(errors='replace')[-2500:];results={}
 for phase in ('validation','performance'):
  image=ROOT/('sw/build/coremark_validation_1/coremark.hex' if phase=='validation' else 'sw/build/coremark_performance_10/coremark.hex');uartlog=out/(phase+'_uart.txt');inputs.append(image)
  with (out/(phase+'.log')).open('wb') as f:p=subprocess.run([*prefix,linux(out/'obj/Vcommon_tb'),'+image='+linux(image),'+uart='+linux(uartlog)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(out/(phase+'.log')).read_text(errors='replace');u=uartlog.read_text(errors='replace');assert p.returncode==0 and 'COMMON_PASS' in log and 'CRC validation   : PASS' in u,(log[-2500:],u[-1000:])
  m=re.search(r'COMMON_WINDOW cycles=(\d+) retired=(\d+) side=(\d+) early_direct=(\d+) pc_hash=(\w+)',log);assert m;results[phase]=dict(cycles=int(m[1]),retired=int(m[2]),side=int(m[3]),early_direct=int(m[4]),pc_hash=m[5],ipc=int(m[2])/int(m[1]),image_sha256=sha(image))
 x=dict(status='PASS',target=a.target,scope='Same binary and same nc_local_bus/Pango functional RAM service, frozen Round50 CPU versus isolated new CPU; excludes original SoC bus and PNR comparison',results=results,input_sha256={str(p.relative_to(ROOT.parent) if not p.is_relative_to(ROOT) else p.relative_to(ROOT)):sha(p) for p in inputs})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(a.target,json.dumps(results))
if __name__=='__main__':main()
