# mipsHelper 2.0

import argparse
import re

from isa import instructions, opcodes, regs

# Struct to hold instruction information
class Instruction():
	''' Constructor
		inTemplate is a list of strings
		outTemplate is a list of strings
		opcode is the 5 digit opcode as a string
		function is the (optional) 6 digit function code as a string
	'''
	def __init__(self, inTemplate, outTemplate, opcode, function):
		self.inTemplate = inTemplate
		self.outTemplate = outTemplate
		self.opcode = opcode
		self.function = function

# Main parser class
class Parser():
	def __init__(self):
		# Reset code base trackers
		self.pc = 0 # PC counter
		self.labels = {}
		self.instrOut = []
		self.dataOut = []
		self.jumpQueue = []
		self.branchQueue = []
		self.registers = {}
		self.instructions = {}
		# Read default ISA file
		self.readISA()
		
	# Returns True if s is convertible to integer
	def isInteger(self, s):
		try:
			int(s, 0)
			return True
		except ValueError:
			return False

	# Returns signed binary version of n with bits digits, as string
	def signedBinary(self, n, bits):
		s = bin(n & int('1'*bits, 2))[2:]
		return ("{0:0>%s}" % (bits)).format(s)

	# Helper function that removes comments (marked by #) from a line
	# Return cleaned line as string
	def removeComments(self, string):
		index = string.find('#')
		if (index != -1):
			string = string[:index]
		return string.strip()
	
	# Break a line into individual words, trimming whitespace and removing comments
	# Return tokenized line as list of strings
	def tokenizeLine(self, line):
		# Regex breakdown: comma followed by spaces OR comma OR parentheses OR spaces
		split = re.split(',\s+|,|\s*\(|\)\s*|\s+', line)
		split = filter(None, split) # Remove empty strings
		return split

	# Reads a ISA reference for parsing templates
	def readISA(self, filename='isa.data'):
		with open(filename, 'r') as f:
			for line in f:
				line = self.removeComments(line)
				splitLine = line.split('-')
		
				# Register
				if (len(splitLine) == 2):
					self.registers[splitLine[0].strip()] = splitLine[1].strip()
		
				# Instructions
				elif (len(splitLine) == 4 or len(splitLine) == 5):
					inSyntax = splitLine[1].split()
					outSyntax = splitLine[2].split()
					opcode = splitLine[3].strip()
					if (len(splitLine) == 5):
						function = splitLine[4].strip()
					else:
						function = ""
					self.instructions[splitLine[0].strip()] = Instruction(inSyntax, outSyntax,
																opcode, function)

	# Parse an instruction (as a split line)
	# Return instruction in binary as string
	def parseInstruction(self, instruction):
		if (len(instruction) > 0):
			op = instruction[0]
			# Do some error checking
			if (op not in self.instructions
					or len(instruction) != (len(self.instructions[op].inTemplate) + 1)):
				print('WARNING: Invalid instruction %s detected, skipping' % op)
				return ""

			# Extract instruction information
			instr = self.instructions[op]
			tokens = {}

			# Parse input instruction (MIPS)
			for (token, value) in zip(instr.inTemplate, instruction[1:]):
				tokens[token] = value

			# Create output instruction (binary)
			outInstruction = ""
			for token in instr.outTemplate:
				# OpCode field
				if (token == 'opcode'):
					outInstruction += instr.opcode
				# Function field
				elif (token == 'function'):
					outInstruction += instr.function
				# Special field(s)
				elif (token not in tokens):
					outInstruction += self.registers[token]
				# Fields from function call
				else:
					# Register
					if (tokens[token] in self.registers):
						outInstruction += self.registers[tokens[token]]
					# Literal fields
					else:
						value = tokens[token]
						# shift fields
						if (token == 'shift'):
							outInstruction += self.signedBinary(int(value, 0), 5)
						# imm16 fields (I type instructions)
						elif (self.isInteger(value)):
							outInstruction += self.signedBinary(int(value, 0), 16)
						# index fields (jumps), where value is the label
						elif (token == 'index'):
							self.jumpQueue.append((self.pc/4, value))
						# offset fields (branches). Note that offsets may be handled as imm16s above 
						elif (token == 'offset'):
							self.branchQueue.append((self.pc/4, value))
			return outInstruction

	# Parse a tokenized line into a binary string
	# Note that this wraps around parseInstruction and adds PC handling etc
	def processInstructionLine(self, splitLine, comment=""):
		# Label detected
		if splitLine[0][-1] == ':':
			self.labels[splitLine[0].rstrip(':')] = self.pc
			# If line is label only, skip everything else
			if len(splitLine) == 1:
				return
			startIndex = 1
		else:
			startIndex = 0
			
		# Parse instruction
		parsed = self.parseInstruction(splitLine[startIndex:])
			
		# Push parsed instruction (pending jump/branch addresses) to list
		self.instrOut.append([parsed, comment]) # (Instruction, Comment)
		self.pc += 4
	
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
			mode = 'instructions' # Default instruction mode
			
			for line in f:
				lineNumber = lineNumber + 1
				line = self.removeComments(line)	
				split = self.tokenizeLine(line)
				
				# Ignore empty lines
				if (len(split) == 0):
					continue

				# Catch special tags
				if (split[0][0] == '.'):
					# DEBUG ONLY!
					if (split[0] == '.data'):
						mode = 'data'
					elif (split[0] == '.text'):
						mode = 'instructions'
					# Don't continue parsing a tag
					continue
				
				if (mode == 'data'):
					# TODO
					pass

				elif (mode == 'instructions'):
					# Line containing just a label
					if len(split) == 1 and split[0][-1] == ':':
						takeMeOn = split[0]
					elif takeMeOn:
						line = takeMeOn + ' ' + line
						takeMeOn = None
					
					self.processInstructionLine(split, line)
		
			# Add branch addresses
			for branch in self.branchQueue:
				branchAddr = self.labels[branch[1]]/4 - (branch[0] + 1)
				self.instrOut[branch[0]][0] += self.signedBinary(branchAddr, 16)
			
			# Add jump addresses
			for jump in self.jumpQueue:
				jumpAddr = self.labels[jump[1]]/4
				self.instrOut[jump[0]][0] += self.signedBinary(jumpAddr, 26)
				
			# Error check instructions
			instructionCounter = 1
			for instruction in self.instrOut:
				# Sanity checks
				if len(instruction[0]) != 32:
					# Incorrect length
					print('WARNING: Length sanity check failed.'
							' Instruction length %d != 32' % len(instruction[0]))
					print('         Original instruction (#%d): %s' 
							% (instructionCounter + 1, instruction[1]))
					print('         Forcing instruction to nop')
					instruction[0] = format(0, '032b') # nop
				instructionCounter = instructionCounter + 1
					
	# Format an output instruction line, where line is a 2-tuple with
	# line[0] being the instruction and line[1] being the comment
	# Returns formatted string
	def formatLineOut(self, line, comment="", lineNumber=None,
					binaryOutput=False, assembler=True, enableComments=True):
		# Convert formatting to hex
		if binaryOutput:
			instruction = line
		else:
			instruction = "{0:0{1}x}".format(int(line,2),8)
			
		# Prepend // to comment to actually make it a comment
		if (enableComments and len(comment) > 0):
			comment = '// ' + comment 
		else:
			comment = ""
			
		# Format output
		if assembler:
			assert(lineNumber is not None)
			output = ('memory[%d] = 32\'%s%s;\t%s'
						% (lineNumber, ('b' if binaryOutput else 'h'),
							instruction, comment))
		else:
			output = '%s\t%s' % (instruction, comment)
		return output
			
	# Print output to console
	def printOutput(self, binaryOutput=False, instructionMemory=False,
					dataMemory=False, assembler=False, comments=False):
		print("\n================================================"
			  "\nResult:"
			  "\n================================================")
		# Write instruction output
		if instructionMemory:
			lineCounter = 0;
			for line in self.instrOut:
				# Format output
				output = self.formatLineOut(line=line[0], comment=line[1],
								lineNumber=lineCounter, binaryOutput=binaryOutput,
								assembler=assembler, enableComments=comments)
				
				# Print output
				print(output)
					
				# Increment counter
				lineCounter = lineCounter + 1
			
		# TODO: Write data output
		if dataMemory:
			lineCounter = 0 ;
			for line in self.dataOut:
				pass
	
	# Write output to file
	def writeOutput(self, outputFile, binaryOutput=False, comments=False,
					instructionMemory=False, dataMemory=False, assembler=False):
		# Check to make sure we have instructions to write
		if (instructionMemory and len(self.instrOut) > 0):
			# If we are writing an instruction file, add _data to our data filename
			filenameSplit = outputFile.rsplit('.',1)
			dataFilename = filenameSplit[0] + '_data.' + filenameSplit[1]
			# Write instruction output
			with open(outputFile, 'w') as f:
				lineCounter = 0;
				for line in self.instrOut:
					# Format output
					output = self.formatLineOut(line=line[0], comment=line[1],
								lineNumber=lineCounter, binaryOutput=binaryOutput,
								assembler=assembler, enableComments=comments)
					
					# Write output
					f.write(output + '\n')
						
					# Increment counter
					lineCounter = lineCounter + 1
		# Not writing instructions, just write data to outputFile
		else:
			dataFilename = outputFile
	
		# Make sure we have data to write
		if (dataMemory and len(self.dataOut) > 0):
			# TODO: Write data output
			with open(dataFilename, 'w') as f:
				# TODO: Write data output
				lineCounter = 0 ;
				for line in self.dataOut:
					pass
		
def main():
	argparser = argparse.ArgumentParser(description="Translate MIPS assembly into binary")
	argparser.add_argument('-a', action="store_true", help="Assembler enable flag")
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
							instructionMemory=args.v, dataMemory=args.d,
							assembler=args.a, comments=args.x)
		else:
			parser.printOutput(binaryOutput=args.b,
							instructionMemory=args.v, dataMemory=args.d,
							assembler=args.a, comments=args.x)
	else:
		print('No input file specified. Use python mipsConverter.py -h for help. Exiting.')
		
	return 0

if __name__ == '__main__':	
	main()
