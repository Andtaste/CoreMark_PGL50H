`timescale 1ns/1ps
module execute_equivalence_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,fetch_error=0;reg[31:0] insn=0,pc=0,a=0,b=0,prediction=0;
 wire[3:0] kind;wire[31:0] imm;wire[4:0] rs1,rs2,rd;
 wire use1,use2,wr,serial,illegal;wire[18:0] control;
 nc_decode decode(.insn(insn),.kind(kind),.imm(imm),.use1(use1),.use2(use2),
  .write_rd(wr),.serial(serial),.illegal(illegal),.rs1(rs1),.rs2(rs2),.rd(rd),
  .csr_exists(1'b1),.csr_writable(1'b1),.control(control));
 wire[203:0] packet={kind,pc,insn,a,b,imm,32'h12345678,rd,wr,illegal,fetch_error};
 wire[276:0] current_packet,old_packet,prior_packet;wire needed,prior_needed,prediction_wrong;wire[31:0] target,prior_target,memory_aux;
 nc_execute current(.clk(clk),.rst_n(rst_n),.clear(1'b0),.valid(1'b0),.ready(),
  .packet(packet),.control(control),.out_valid(),.out_ready(1'b1),.out_packet(current_packet),
  .prediction(prediction),.prediction_wrong(prediction_wrong),.branch_taken(),
  .redirect_needed(needed),.redirect_target(target),.memory_aux(memory_aux));
 old_nc_execute reference(.clk(clk),.rst_n(rst_n),.clear(1'b0),.valid(1'b0),.ready(),
  .packet(packet),.out_valid(),.out_ready(1'b1),.out_packet(old_packet));
 prior_nc_execute prior(.clk(clk),.rst_n(rst_n),.clear(1'b0),.valid(1'b0),.ready(),
  .packet(packet),.control(control),.out_valid(),.out_ready(1'b1),.out_packet(prior_packet),
  .redirect_needed(prior_needed),.redirect_target(prior_target));
 integer i,j,seed=20261020,choice,branches=0,redirects=0;reg[2:0] f3;reg[6:0] f7;
 reg[11:0] im12;reg expected;
 integer aux_checks=0;reg[31:0] expected_aux;
 task check_aux(input[276:0] reference_packet);
  begin
   // Reference EX computes the old architectural packet independently.
   // Valid memory/CSR words retain their payload even without an exception;
   // otherwise a fault MUST expose exactly the reference tval. A successful
   // branch may carry next-PC in the otherwise ignored auxiliary field.
   if(!illegal && !fetch_error && (kind==4 || kind==5)) expected_aux=reference_packet[148:117];
   else if(!illegal && !fetch_error && kind==7) expected_aux=reference_packet[52:21];
   else if(reference_packet[2]) expected_aux=reference_packet[84:53];
   else if(kind>=1 && kind<=3) expected_aux=reference_packet[212:181];
   else expected_aux=0;
   if(memory_aux!==expected_aux) $fatal(1,"MEM aux mismatch insn=%h pc=%h got=%h expected=%h",insn,pc,memory_aux,expected_aux);
   aux_checks=aux_checks+1;
  end
 endtask
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  for(i=0;i<24000;i=i+1) begin
   pc=$random(seed)&32'hfffffffc;a=$random(seed);b=$random(seed);
   if(i%97==0) pc=pc|2; // Also retain old semantics for bad-PC packets.
   f3=$random(seed);f7=0;im12=$random(seed);choice=i%16;
   case(choice)
    0:begin
     if((f3==0 || f3==5) && i%3==0) f7=7'h20;
     insn={f7,5'd2,5'd1,f3,5'd3,7'h33};
    end
    1:begin
     if(f3==1) im12={7'b0,im12[4:0]};
     if(f3==5) im12={(i%3==0 ? 7'h20 : 7'b0),im12[4:0]};
     insn={im12,5'd1,f3,5'd3,7'h13};
    end
    2:insn=($random(seed)&32'hfffff000)|32'h1b7;
    3:insn=($random(seed)&32'hfffff000)|32'h197;
    4,5,6,7,8,9:begin
     case(choice) 4:f3=0;5:f3=1;6:f3=4;7:f3=5;8:f3=6;9:f3=7;endcase
     insn=($random(seed)&32'hfe000f80)|{7'b0,5'd2,5'd1,f3,5'b0,7'h63};
     if(i%3==0) insn={7'b0,5'd2,5'd1,f3,5'd4,7'h63}; // offset=4
     if(i%5==0) b=a;
    end
    10:begin insn=($random(seed)&32'hfffff000)|32'h1ef;if(i%3==0) insn=32'h004001ef;end
    11:begin
     insn={im12,5'd1,3'b0,5'd3,7'h67};#1;
     if(i%3==0) a=pc+4-imm;
     if(i%5==0) a=pc+5-imm; // JALR low-bit clear can still be sequential.
    end
    12:insn={im12,5'd1,3'b010,5'd3,7'h03};
    13:insn={im12[11:5],5'd2,5'd1,3'b001,im12[4:0],7'h23};
    14:begin if(f3==0 || f3==4) f3=3'b110;insn={12'h340,5'd1,f3,5'd3,7'h73};end
    15:case(i%5) 0:insn=32'h00000073;1:insn=32'h00100073;2:insn=32'h30200073;
       3:insn=32'h0000100f;4:insn=32'h10500073;endcase
   endcase
   #2;
   if(illegal) $fatal(1,"bad test generator %h",insn);
   if(current_packet!==old_packet) $fatal(1,"EX equivalence i=%0d insn=%h pc=%h a=%h b=%h got=%h expected=%h",i,insn,pc,a,b,current_packet,old_packet);
   check_aux(old_packet);
   expected=kind>=1 && kind<=3 && !old_packet[2] && old_packet[212:181]!=(pc+32'd4);
   if(needed!==expected || (needed && target!==old_packet[212:181]))
    $fatal(1,"redirect equivalence insn=%h pc=%h",insn,pc);
   if(kind>=1 && kind<=3) branches=branches+1;
   if(needed) redirects=redirects+1;
  end
  $display("PASS execute equivalence vectors=%0d branches=%0d redirects=%0d",i,branches,redirects);
  // Additional full-packet comparison with the immediate baseline covers
  // illegal instructions, fetch faults, bad PCs, alignment and priority.
  for(i=0;i<8000;i=i+1) begin
   pc=$random(seed);a=$random(seed);b=$random(seed);fetch_error=i%3!=0;
   case(i%8)
    0:insn=32'hffffffff;
    1:insn=32'h00002063; // illegal branch funct3
    2:insn=32'h00008067; // JALR
    3:insn=32'h00208463; // BEQ
    4:insn=32'h0000a183; // LW
    5:insn=32'h0020a023; // SW
    6:insn=32'h00100073; // EBREAK
    7:insn=$random(seed);
   endcase
   #2;
   if(current_packet!==prior_packet || needed!==prior_needed || target!==prior_target)
    $fatal(1,"fault equivalence i=%0d insn=%h fetch_fault=%b got=%h expected=%h",i,insn,fetch_error,current_packet,prior_packet);
   check_aux(prior_packet);
  end
  $display("PASS execute fault-priority equivalence vectors=%0d",i);
  for(i=0;i<3000;i=i+1) begin
   pc=$random(seed);a=$random(seed);b=$random(seed);fetch_error=i%13==0;
   case(i%6)
    0,1:insn=($random(seed)&32'hfe000f80)|32'h00208063;
    2:insn=($random(seed)&32'hfff00000)|32'h000081e7;
    3:insn=($random(seed)&32'hfffff000)|32'h000001ef;
    4:insn=32'h00108093;
    5:insn=$random(seed);
   endcase
   #2;
   for(j=0;j<4;j=j+1) begin
    case(j)
     0:prediction=0;
     1:prediction={2'b11,prior_packet[212:183]};
     2:prediction={2'b11,(pc[31:2]+30'd1)};
     3:prediction={2'b11,(prior_packet[212:183]^30'h400)};
    endcase
    #2;
    expected=!prior_packet[2] && (prediction[30] ? {prediction[29:0],2'b0} : pc+32'd4)!=prior_packet[212:181];
    if(prediction_wrong!==expected || current_packet!==prior_packet)
     $fatal(1,"prediction check i=%0d j=%0d insn=%h pred=%h actual=%h",i,j,insn,prediction,prior_packet[212:181]);
    check_aux(prior_packet);
   end
  end
  $display("PASS execute prediction checks=12000");
  $display("PASS execute memory-aux checks=%0d",aux_checks);$finish;
 end
endmodule
