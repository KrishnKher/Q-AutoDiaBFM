# compare the diff lines
# note that there are only a finite number of inbuilt gates in qiskit
# provided the identifier is the same, check if the other files' gate matches with an inbuilt gate.
# incase it is a custom made gate, think
import ast
import re
import numpy as np
from code_diff.diff_utils import parse_hunks
from code_diff import SStubPattern
import code_diff as cd

def returnArgs(args):
    args = "".join(args.split(" "))
    square = []
    paren = []  
    value = ""
    parenCheck = 0
    squareCheck = 0

    for char in args:
        if char == '(':
            parenCheck = 1
        elif char == '[':
            squareCheck = 1
        elif char == ']':
            squareCheck = 0
            square.append(value)
            paren.append(square)
            square = []
            value = ""
        elif char == ')':
            parenCheck = 0
            if len(value) > 0:
                paren.append(value)
        elif char == ',':
            if parenCheck and value != "":
                if squareCheck:
                    square.append(value)
                else:
                    paren.append(value)
            value = ""
        else:
            value += char
    
    for args in range(len(paren)):
        if isinstance(paren[args], list):
            for index in range(len(paren[args])):
                paren[args][index] = eval(paren[args][index])
        else:
            paren[args] = eval(paren[args])
    
    return np.array(paren)

def measurementRegisterError(codeSample):
    availableMeasurementFunctions = ['measure', 'measure_all', 'measure_inactive']
    regexPattern = ".+\.measure.*"
    # " *Update\(\(identifier:.+, *line [0-9]+:[0-9] - [0-9]+:[0-9]\), .+\) * "

    buggy, patched = codeSample[0], codeSample[2]
    buggyID, patchedID = {}, {}
    buggyMeasure, patchedMeasure = {}, {}
    buggyList = list(filter(("").__ne__, buggy.split("\n")))
    patchedList = list(filter(("").__ne__, patched.split("\n")))
    buggyLine, patchedLine = {}, {}
    buggyArgs, patchedArgs = [], []
    astBuggy, astPatched = ast.walk(ast.parse(buggy)), ast.walk(ast.parse(patched))
    
    for node in astBuggy:
        if isinstance(node, ast.Assign):
            for id in getattr(node, 'targets'):
                if id.id not in buggyID and getattr(node, 'value').func.id == "QuantumCircuit":
                    buggyID[id.id] = []
        
        #Check if any of the measure function is present in the code
        #Using AST to perform this check
        if isinstance(node, ast.Expr):
            if getattr(node, "value").func.attr in availableMeasurementFunctions:
                if getattr(node, "value").func.value.id not in buggyMeasure:
                    buggyMeasure[getattr(node, "value").func.value.id] = [] 
                    buggyMeasure[getattr(node, "value").func.value.id].append(getattr(node, "value").func.attr)
                else:
                    buggyMeasure[getattr(node, "value").func.value.id].append(getattr(node, "value").func.attr)
    
    for node in astPatched:
        if isinstance(node, ast.Assign):
            for id in getattr(node, 'targets'):
                if id.id not in patchedID and getattr(node, 'value').func.id == "QuantumCircuit":
                    patchedID[id.id] = []
        
        #Check if any of the measure function is present in the code
        #Using AST to perform this check
        if isinstance(node, ast.Expr):
            if getattr(node, "value").func.attr in availableMeasurementFunctions:
                if getattr(node, "value").func.value.id not in patchedMeasure:
                    patchedMeasure[getattr(node, "value").func.value.id] = [] 
                    patchedMeasure[getattr(node, "value").func.value.id].append(getattr(node, "value").func.attr)
                else:
                    patchedMeasure[getattr(node, "value").func.value.id].append(getattr(node, "value").func.attr)
    
    ''' Considering the cases when there is a one to one mapping of the QuantumCircuits 
    in buggy code to the QuantumCircuits in patched code. '''

    if len(buggyID) != len(patchedID):
        return False
    
    #Considering only one quantum circuit, will fail otherwise
    #The below semantic check verifies if the same mesurement function is being used 
    if len(buggyMeasure) != len(patchedMeasure):
        return True
    
    buggyKeys, patchedKeys = list(buggyMeasure.keys()), list(patchedMeasure.keys())

    for i in range(len(buggyKeys)):
        if buggyMeasure[buggyKeys[i]] != patchedMeasure[patchedKeys[i]]:
            return True
    
    for line in range(len(buggyList)):
        tempStatus = re.search(regexPattern, buggyList[line])
        if tempStatus is not None:
            buggyLine[buggyList[line].split("measure")[1]] = line
    
    for line in range(len(patchedList)):
        tempStatus = re.search(regexPattern, patchedList[line])
        if tempStatus is not None:
            patchedLine[patchedList[line].split("measure")[1]] = line

    for buggyKey in buggyLine.keys():
        buggyArgs.append(returnArgs(buggyKey))
    
    for patchedKey in patchedLine.keys():
        patchedArgs.append(returnArgs(patchedKey))
    
    if len(buggyArgs) != len(patchedArgs):
        return False

    for i in range(len(buggyArgs)):
        if buggyArgs[i].shape != patchedArgs[i].shape:
            return True
        else:
            if np.array_equal(buggyArgs[i], patchedArgs[i]) == 0:
                return True
    
    buggyLineNum = list(buggyLine.values())
    patchedLineNum = list(patchedLine.values())
    
    for num in range(len(buggyLineNum)):
        if buggyLineNum[num] != patchedLineNum[num]:
            return True
    
    return False

def detectIncorrectMeasurement(codeSample):
    status = False
    bugTypeMessage = "Measurement(s) performed incorrectly."
    status = measurementRegisterError(codeSample)

    # again done only with a quantum circuit object.
    # 1. If the arguments are not matching then something is off.
    # 2. Or if it is measured in the wrong place in the code. Not hhandling right now?



    return status, bugTypeMessage