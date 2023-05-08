'''
The following code-pair contains an IncorrectInit bug.
'''

buggyCode = '''
qc = QuantumCircuit(1)
qc.h(0)
qc.draw()
'''

patchedCode = '''
qc = QuantumCircuit(3)
qc.h(0)
qc.draw()
'''