# mipsHelper 2.0

import argparse
import re

parser = argparse.ArgumentParser(description="Translate MIPS assembly into binary")
#parser.add_argument('-a', action="store_true", help="Assembler enable flag")
parser.add_argument('-i', metavar='input_file', type=argparse.FileType('rt'), help="Input file name")
parser.add_argument('-o', metavar='output_file', type=argparse.FileType('wt'), help="Output file name")
# parser.add_argument('-d', action="store_true", help="output data memory (will create separate data file)")
parser.add_argument('-b', action="store_true", help="output in binary (default hex)")
# parser.add_argument('-v', action="store_true", help="output 32-bit instruction memory")
parser.add_argument('-x', action="store_true", help="include MIPS instructions as comments")

# Testing only
args = parser.parse_args()

# Flags to ignore, e.g. comments etc
ignore = ['.', '#']

# Instructions
instr = {'add' : '000000',
		 'sub' : '000000',
		 'addi': '001000',
		 'and' : '000000',
		 'andi': '001100',
		 'sll' : '000000',
		 'srl' : '000000',
		 'sra' : '000000',
		 'beq' : '000100',
		 'bne' : '000101',
		 'j'   : '000010',
		 'jal' : '000011',
		 'jr'  : '000000',
		 # Custom instructions
		 'blte' :  '110100',
		 'lsad':  '111000',
		 'sad' :  '111001',
	}

# OpCodes
opcode = {'add' : '100000',
          'sub' : '100010',
          'addi': 'N/A',
          'and' : '100100',
          'andi': 'N/A',
          'sll' : '000000',
          'srl' : '000010',
          'sra' : '000011',
          'beq' : 'N/A',
          'bne' : 'N/A',
          'j'   : 'N/A',
          'jal' : 'N/A',
          'jr'  : '001000',
          'blte' : 'N/A',
          'sad' : '000000',
          'lsad': '000000',
	}
	
# Registers
regs = {'$0': 0, '$zero': 0,
		'$1': 1, '$at': 1,
		'$2': 2, '$v0': 2,
		'$3': 3, '$v1': 3,
		'$4': 4, '$a0': 4,
		'$5': 5, '$a1': 5,
		'$6': 6, '$a2': 6,
		'$7': 7, '$a3': 7,
		'$8': 8, '$t0': 8,
		'$9': 9, '$t1': 9,
		'$10': 10, '$t2': 10,
		'$11': 11, '$t3': 11,
		'$12': 12, '$t4': 12,
		'$13': 13, '$t5': 13,
		'$14': 14, '$t6': 14,
		'$15': 15, '$t7': 15,
		'$16': 16, '$s0': 16,
		'$17': 17, '$s1': 17,
		'$18': 18, '$s2': 18,
		'$19': 19, '$s3': 19,
		'$20': 20, '$s4': 20,
		'$21': 21, '$s5': 21,
		'$22': 22, '$s6': 22,
		'$23': 23, '$s7': 23,
		'$24': 24, '$t8': 24,
		'$25': 25, '$t9': 25,
		'$26': 26, '$k0': 26,
		'$27': 27, '$k1': 27,
		'$28': 28, '$gp': 28,
		'$29': 29, '$sp': 29,
		'$30': 30, '$fp': 30,
		'$31': 31, '$ra': 31,
	}

def isInteger(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def signedBinary(n, bits):
	s = bin(n & int('1'*bits, 2))[2:]
	return ("{0:0>%s}" % (bits)).format(s)
		
def main():
	try:
		pc = 0 # PC counter
		labels = {}
		instrOut = []
		jumpQueue = []
		branchQueue = []
		
		if args.i is not None:
			for line in args.i:
				line = line.lstrip()
				# Ignore empty lines and special lines
				if len(line) == 0 or line[0] in ignore:
					continue
				split = re.split('\s+|,\s+|,', line) # Tokenize, removing spaces and commas
				split = filter(None, split) # Remove empty strings
				
				# Label detected
				if split[0][-1] == ':':
					# Label is NOT only element on line, and contains actual instruction
					if len(split) != 1 and split[1][0] not in ignore:
						pc += 4
					# if not, do NOT increase PC. We'll do that on next instruction
					labels[split[0].rstrip(':')] = pc
			
				# If not a label, proceed as normal
				else:
					# Parse instruction
					parsed = ""
					# Check instruction is in dictionary and not empty (not implemented)
					if (split[0] in instr and len(instr[split[0]]) != 0):
						parsed += instr[split[0]]
						# R Type (SPECIAL)
						if (parsed == '000000'):
							# Shifts (Uses SA)
							if (int(opcode[split[0]], 2) < 4):
								parsed += '00000' # unused rs field
								parsed += format(regs[split[2]], '05b') # rt
								parsed += format(regs[split[1]], '05b') # rd
								parsed += format(int(split[3]), '05b') # rs
								parsed += opcode[split[0]]
							else:
								parsed += format(regs[split[2]], '05b') # rs
								parsed += format(regs[split[3]], '05b') # rt
								parsed += format(regs[split[1]], '05b') # rd
								parsed += '00000' # unused sa field
								parsed += opcode[split[0]]
						
						# TODO: SPECIAL2
						elif (parsed == '011100'):
							pass
						# TODO: SPECIAL3
						elif (parsed == '011111'):
							pass

						# J Type (J and JAL)
						elif (parsed == '000010' or parsed == '000011'):
							jumpQueue.append((pc/4, split[1]))
						
						# Custom SAD instructions
						elif (parsed[0:3] == '111'):
							# lsad
							if (parsed[-1] == '0'):
								parsed += format(regs[split[1]], '05b') # rs
								parsed += format(regs[split[2]], '05b') # rt
								parsed += '0000000000000000' # unused 16 bit slot
							# sad/sadn
							elif (parsed[-1] == '1'):
								parsed += '00000' # unused rs slot
								parsed += format(regs[split[2]], '05b') # rt
								parsed += format(regs[split[1]], '05b') # rd
								parsed += '00000' # unused sa slot
								parsed += '000000' # unused opcode slot
								
						# I Type
						else:
							if (len(split) < 4 or split[1] not in regs or split[2] not in regs):
								# Error has occurred
								parsed = format(0, '032b') # nop
							else:
								# TODO: Error checking
								# Regular imm type
								if isInteger(split[3]):
									parsed += format(regs[split[2]], '05b') # rs
									parsed += format(regs[split[1]], '05b') # rt
									parsed += signedBinary(int(split[3]), 16)
								# Branch
								else:
									parsed += format(regs[split[1]], '05b') # rs
									parsed += format(regs[split[2]], '05b') # rt
									branchQueue.append((pc/4, split[3])) # Push (instrNum, label) to queue
					
					instrOut.append([parsed, '//' + line.split('#', 1)[0].rstrip()]) # (Instruction, Comment)
					pc += 4
			
			for line in branchQueue:
				branchAddr = labels[line[1]]/4 - (line[0] + 1)
				instrOut[line[0]][0] += signedBinary(branchAddr, 16)
			
			for line in jumpQueue:
				jumpAddr = labels[line[1]]/4
				instrOut[line[0]][0] += signedBinary(jumpAddr, 26)
			
			if not args.o:
				print "\n\nResult:"
				
			for line in instrOut:
				# Hex?
				if (args.b == False):
					line[0] = "{0:0{1}x}".format(int(line[0],2),8)
					
				if (args.o == None):
					print line[0] + '\t' + line[1]
				else:
					args.o.write(line[0] + '\t' + line[1] + '\n')
		else:
				print('No input file specified. Use python mipsConverter.py -h for help. Exiting.')
			
	except IOError, msg:
		parser.error(str(msg))
		
	return 0

if __name__ == '__main__':	
	main()
