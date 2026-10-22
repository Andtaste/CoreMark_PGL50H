Verified82MHz placement for CoreMark5000. This is independent of the old fixed10 checkpoint.
Use tools/build_board5000.py: fresh RTL synthesis, exact input and full connectivity check, frozen placement0, route1, four-corner timing gate, bitstream generation.
Modified sources/images/constraints invalidate this checkpoint. Do not bypass the guard.
