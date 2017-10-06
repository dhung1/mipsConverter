## mipsConverter  
This is a helper script which converts MIPS assembly code into its binary 
equivalent, including optional Verilog support. This was originally created 
for ECE 369 at the University of Arizona  

To check usage, simply invoke  
```
python mipsConverter.py -h
```  

Some important options are:

```
-a Enables the assembler, which formats output as Verilog code
-v Enables instruction output
-d Enables data memory output
-x Adds the original MIPS instructions as comments to each line
```

__NOTE THAT YOU MUST USE THE -v AND -d FLAGS TO ENABLE OUTPUT!__ Omitting 
these flags will produce a blank output

Typical usage will likely look like:  
```
python mipsConverter.py -i mips_code.s -o verilog_code.v -avdx
```  

This will read in the MIPS code in `mips_code.s` and output two files:  
- `verilog_code.v` will include the instruction memory as verilog code
- `verilog_code_data.v` will include the data memory as verilog code (WIP)

This script is a work in progress. If you are interested in contributing, 
please reach out to davidhung@email.arizona.edu
