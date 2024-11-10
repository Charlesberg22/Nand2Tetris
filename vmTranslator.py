import os
import sys
import textwrap

class Parser:
    def __init__(self, path):
        self.line_number = 0
        self.filename = self._return_filename(path)
        self.cleaned_code = self._return_cleaned_file(path)
        self._setup_new_line()
    
    def _return_filename(self, path):
        return os.path.basename(path).replace(".vm", "")
    
    def _return_cleaned_file(self, path):
        cleaned_file = []
        file = open(path, 'r')
        code = file.readlines()
        file.close()
        for line in code:
            cleaned_line = line.strip().split("//")[0].strip()
            if cleaned_line:
                cleaned_file.append(cleaned_line)
        return cleaned_file
    
    def _setup_new_line(self):
        self.current_line = None
        self.command_type = None
        self.arg1 = None
        self.arg2 = None

    def has_more_lines(self):
        return len(self.cleaned_code) > 0
    
    def advance(self):
        self._setup_new_line()
        self.line_number = self.line_number + 1
        self.current_line = self.cleaned_code.pop(0)
        self._parse_line(self.current_line)

    def _parse_line(self, line):
        if line in ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]:
            self.command_type = "C_ARITHMETIC"
            self.arg1 = line
        elif line.startswith("push"):
            self.command_type = "C_PUSH"
        elif line.startswith("pop"):
            self.command_type = "C_POP"
        elif line.startswith("function"):
            self.command_type = "C_FUNCTION"
        elif line.startswith("call"):
            self.command_type = "C_CALL"
        elif line.startswith("label"):
            self.command_type = "C_LABEL"
        elif line.startswith("goto"):
            self.command_type = "C_GOTO"
        elif line.startswith("if-goto"):
            self.command_type = "C_IF"
        elif line.startswith("return"):
            self.command_type = "C_RETURN"
        if self.command_type in ["C_PUSH", "C_POP", "C_FUNCTION", "C_CALL"]:
            args = line.split(" ")
            self.arg1 = args[1]
            self.arg2 = int(args[2])
        elif self.command_type in ["C_LABEL", "C_IF", "C_GOTO"]:
            self.arg1 = line.split(" ")[1]

class CodeWriter:
    def __init__(self, path):
        self.output_file = open(path, 'w')
        self.locations = {
            "local": "LCL",
            "argument": "ARG",
            "this": "THIS",
            "that": "THAT",
            "pointer": "3",
            "temp": "5"
        }
        self.address_number = 1
        self.filename = self._return_filename(path)
    
    def _return_filename(self, path):
        return os.path.basename(path).replace(".asm", "")

    def close(self):
        self._write_infinite_loop()
        self.output_file.close()

    def _write_infinite_loop(self):
        line = ["(END)", "@END", "0;JMP"]
        self._write_line(line)

    def _write_line(self, line):
        for asm_line in line:
            self.output_file.write(asm_line)
            self.output_file.write("\n")
        
    def write_arithmetic(self, command):
        if command == "neg":
            details = ["M=-M", "@SP", "M=M+1"]
        elif command == "not":
            details = ["M=!M", "@SP", "M=M+1"]
        elif command in ["add", "sub", "or", "and", "eq", "gt", "lt"]:
            if command == "add":
                operation = ["D=D+M", "M=D"]
            elif command == "sub":
                operation = ["D=M-D", "M=D"]
            elif command == "or":
                operation = ["M=D|M"]
            elif command == "and":
                operation = ["M=D&M"]
            elif command in ["eq", "gt", "lt"]:
                operation = [
                    "D=M-D",
                    "@{}_{}".format(command.upper(), self.address_number),
                    "D;J{}".format(command.upper()), "@SP", "A=M-1", "M=0",
                    "@END_{}".format(self.address_number), "0;JMP",
                    "({}_{})".format(command.upper(), self.address_number),
                    "@SP", "A=M-1", "M=-1", "(END_{})".format(self.address_number)]
                self.address_number += 1
            details = ["D=M", "A=A-1"] + operation
        line = ["// {}".format(command), "@SP", "M=M-1", "A=M"] + details 
        self._write_line(line)

    def write_push_pop(self, command, segment, index):
        if command == "C_PUSH":
            if segment == "constant":
                details = ["@{}".format(index), "D=A"]
            elif segment == "static":
                details = ["@{}.{}".format(self.filename, index), "D=M"]
            else:
                details = ["@{}".format(self.locations[segment]),
                           "D={}".format("A" if (segment == "pointer" or segment == "temp") else "M"),
                           "@{}".format(index),
                           "D=D+A", "A=D", "D=M"]
            line = ["// push {} {}".format(segment, index), "@SP", "A=M", "M=D", "@SP", "M=M+1"]
            line[1:1] = details
        elif command == "C_POP":
            if segment == "static":
                details_a = []
                details_b = ["@{}.{}".format(self.filename, index), "M=D"]
            else:
                details_a = ["@{}".format(self.locations[segment]),
                             "D={}".format("A" if (segment == "pointer" or segment == "temp") else "M"),
                             "@{}".format(index), "D=D+A",
                             "@address_{}".format(self.address_number),
                             "M=D"]
                details_b = ["address_{}".format(self.address_number),
                             "A=M", "M=D"]
                self.address_number += 1
            line = ["// pop {} {}".format(segment, index),
                    "@SP", "M=M-1", "A=M", "D=M"] + details_b
            line[1:1] = details_a
        self._write_line(line)
        
def main():
    input_file = sys.argv[1]
    output_file = input_file.replace(".vm", ".asm")
    translate(input_file, output_file)

def translate(input_file, output_file):
    parser = Parser(input_file)
    code_writer = CodeWriter(output_file)
    while parser.has_more_lines():
        parser.advance()
        if parser.command_type == "C_ARITHMETIC":
            code_writer.write_arithmetic(parser.arg1)
        elif parser.command_type == "C_PUSH" or parser.command_type == "C_POP":
            code_writer.write_push_pop(parser.command_type, parser.arg1, parser.arg2)
    code_writer.close()

main()