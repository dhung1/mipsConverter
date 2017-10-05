# mipsHelper 2.0

import argparse
import re

from isa import instructions, opcodes, regs

# Flags to ignore. # TODO: Remove and handle these flags instead
ignore = ['.']

class Parser():
	def __init__(self):
		# Reset code base trackers
		self.pc = 0 # PC counter
		self.labels = {}
		self.instrOut = []
		self.dataOut = []
		self.jumpQueue = []
		self.branchQueue = []
		
	def isInteger(self, s):
		try:
			int(s)
			return True
		except ValueError:
			return False

	def signedBinary(self, n, bits):
		s = bin(n & int('1'*bits, 2))[2:]
		return ("{0:0>%s}" % (bits)).format(s)
		
	# Break a line into individual words, trimming whitespace and removing comments
	# Return tokenized line
	def tokenizeLine(self, line):
		# Remove comments, marked by #
		index = line.find('#')
		if index != -1:
			line = line[:index]
		
		split = re.split('\s+|,\s+|,', line) # Tokenize, removing spaces and commas
		split = filter(None, split) # Remove empty strings
		return split
		
	# Parse a tokenized line into a binary string
	# Return True on success, False on failure
	def parseTokenizedInstruction(self, splitLine, comment=""):
		error = False
		
		# Label detected
		if splitLine[0][-1] == ':':
			self.labels[splitLine[0].rstrip(':')] = self.pc
			# If line is label only, skip everything else
			if len(splitLine) == 1:
				return not error;
			startIndex = 1
		else:
			startIndex = 0
			
		# Parse instruction
		try:
			parsed = ""
			# Check instruction is in ISA lookup
			instr = splitLine[startIndex]
			if instr in instructions:
				parsed += instructions[instr]
				op = opcodes[instr]
				# R Type (SPECIAL)
				if (parsed == '000000'):
					# Shifts (Uses SA)
					if (int(op, 2) < 4):
						parsed += '00000' # unused rs field
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rt
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rd
						parsed += format(int(splitLine[startIndex+3]), '05b') # rs
						parsed += op
					else:
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+3]], '05b') # rt
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rd
						parsed += '00000' # unused sa field
						parsed += op
				
				# SPECIAL2
				elif (parsed == '011100'):
					# MUL
					if (op == '00010'):
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+3]], '05b') # rt
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rd
						parsed += '00000' # unused sa field
						parsed += op
					# MADD and MSUB
					elif (op == '000000' or op == '000100'):
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rt
						parsed += '00000' # unused rd field
						parsed += '00000' # unused sa field
						parsed += op
					# CLO and CLZ
					elif (op[:-1] == '10000'):
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rt
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rd
						parsed += '00000' # unused sa field
						parsed += op

				# SPECIAL3
				elif (parsed == '011111'):
					parsed += '00000' # unused rs field
					parsed += format(regs[splitLine[startIndex+2]], '05b') # rt
					parsed += format(regs[splitLine[startIndex+1]], '05b') # rd
					if (instr == 'seb'):
						parsed += '10000' # SEB flag
					elif (instr == 'seh'):
						parsed += '11000' # SEH flag

				# J Type (J and JAL)
				elif (parsed == '000010' or parsed == '000011'):
					self.jumpQueue.append((self.pc/4, splitLine[startIndex+1]))
						
				# I Type
				else:
					# TODO: Error checking
					# Regular imm type
					imm = splitLine[startIndex+3]
					if self.isInteger(imm):
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rt
						parsed += self.signedBinary(int(imm), 16)
					# Branch
					else:
						parsed += format(regs[splitLine[startIndex+1]], '05b') # rs
						parsed += format(regs[splitLine[startIndex+2]], '05b') # rt
						self.branchQueue.append((self.pc/4, imm)) # Push (instrNum, label) to queue
				
		except KeyError:
			print('WARNING: KeyError encountered')
			error = True
			parsed = format(0, '032b') # nop
			
		if parsed == "":
			print('WARNING: Invalid instruction')
			error = True
			parsed = format(0, '032b') # nop
		
		# Push parsed instruction (pending jump/branch addresses) to list
		self.instrOut.append([parsed, comment]) # (Instruction, Comment)
		self.pc += 4
		
		return not error
	
	# Parse an input MIPS file, where inputFile is the filename
	def parseFile(self, inputFile):
		with open(inputFile, 'r') as f:
			# Reset code base trackers
			self.pc = 0 # PC counter
			self.labels = {}
			self.instrOut = []
			self.jumpQueue = []
			self.branchQueue = []
			# Reset counter
			lineNumber = 0
			# Carry over variable for labels
			takeMeOn = None
			
			for line in f:
				lineNumber = lineNumber + 1
				split = self.tokenizeLine(line)
				
				# Ignore empty lines and special lines
				if len(split) == 0 or line[0] in ignore:
					continue
				
				# Line containing just a label
				if len(split) == 1 and split[0][-1] == ':':
					takeMeOn = split[0]
					continue
				elif takeMeOn:
					split.insert(0, takeMeOn)
					takeMeOn = None
				
				originalLine = ' '.join(split)
				success = self.parseTokenizedInstruction(split, originalLine)
				if not success:
					print('WARNING: Error encountered while parsing line %d' % lineNumber)
					print('         Original instruction: %s' % originalLine)
		
			# Add branch addresses
			for line in self.branchQueue:
				branchAddr = self.labels[line[1]]/4 - (line[0] + 1)
				self.instrOut[line[0]][0] += self.signedBinary(branchAddr, 16)
			
			# Add jump addresses
			for line in self.jumpQueue:
				jumpAddr = self.labels[line[1]]/4
				self.instrOut[line[0]][0] += self.signedBinary(jumpAddr, 26)
				
			# Error check instructions
			for line in self.instrOut:
				# Sanity checks
				if len(line[0]) != 32:
					# Incorrect length
					print('WARNING: Length sanity check failed.'
							' Instruction length %d != 32' % len(line[0]))
					print('         Forcing instruction #%d to nop'
							% (lineCounter + 1))
					line[0] = format(0, '032b') # nop
					
	# Format an output instruction line, where line is a 2-tuple with
	# line[0] being the instruction and line[1] being the comment
	# Returns formatted string
	def formatInstructionOutput(self, line, lineNumber=None, binaryOutput=False,
					instructionMemory=False, dataMemory=False):
		# Convert formatting to hex
		if binaryOutput:
			instruction = line[0]
		else:
			instruction = "{0:0{1}x}".format(int(line[0],2),8)
			
		# Prepend // to comment to actually make it a comment
		if len(line[1]) > 0:
			comment = '// ' + line[1]
		else:
			comment = "";
			
		# Format output
		if instructionMemory:
			assert(lineNumber is not None)
			output = ('memory[%d] = 32\'%s%s;\t%s'
						% (lineNumber, ('b' if binaryOutput else 'h'),
							instruction, comment))
		else:
			output = '%s\t%s' % (instruction, comment)
		
		return output
			
	# Print output to console
	def printOutput(self, binaryOutput=False,
					instructionMemory=False, dataMemory=False):
		print("\n================================================"
			  "\nResult:"
			  "\n================================================")
		lineCounter = 0;
		# Write instruction output
		for line in self.instrOut:
			# Format output
			output = self.formatInstructionOutput(line=line,
							lineNumber=lineCounter, binaryOutput=binaryOutput,
							instructionMemory=instructionMemory,
							dataMemory=dataMemory)
			
			# Print output
			print(output)
				
			# Increment counter
			lineCounter = lineCounter + 1
			
		# TODO: Write data output
		# TODO: Write data output
		lineCounter = 0 ;
		for line in self.dataOut:
			pass
	
	# Write output to file
	def writeOutput(self, outputFile, binaryOutput=False,
					instructionMemory=False, dataMemory=False):
		# Write instruction output
		with open(outputFile, 'w') as f:
			lineCounter = 0;
			for line in self.instrOut:
				# Format output
				output = self.formatInstructionOutput(line,
							lineNumber=lineCounter, binaryOutput=binaryOutput,
							instructionMemory=instructionMemory,
							dataMemory=dataMemory)
				
				# Write output
				f.write(output + '\n')
					
				# Increment counter
				lineCounter = lineCounter + 1
				
		# TODO: Write data output
		filenameSplit = outputFile.rsplit('.',1)
		dataFilename = filenameSplit[0] + '_data.' + filenameSplit[1]
		with open(dataFilename, 'w') as f:
			# TODO: Write data output
			lineCounter = 0 ;
			for line in self.dataOut:
				pass
		
def main():
	argparser = argparse.ArgumentParser(description="Translate MIPS assembly into binary")
	#argparser.add_argument('-a', action="store_true", help="Assembler enable flag")
	argparser.add_argument('-i', '--input_file', help="Input file name")
	argparser.add_argument('-o', '--output_file', help="Output file name")
	argparser.add_argument('-d', action="store_true", help="output data memory (will create separate data file)")
	argparser.add_argument('-b', action="store_true", help="output in binary (default hex)")
	argparser.add_argument('-v', action="store_true", help="output 32-bit instruction memory")
	argparser.add_argument('-x', action="store_true", help="include MIPS instructions as comments")
	args = argparser.parse_args()

	parser = Parser()
	if args.input_file is not None:
		parser.parseFile(inputFile=args.input_file)
		if args.output_file is not None:
			parser.writeOutput(outputFile=args.output_file, binaryOutput=args.b,
							instructionMemory=args.v, dataMemory=args.d)
		else:
			parser.printOutput(binaryOutput=args.b,
							instructionMemory=args.v, dataMemory=args.d)
	else:
		print('No input file specified. Use python mipsConverter.py -h for help. Exiting.')
		
	return 0

if __name__ == '__main__':	
	main()
