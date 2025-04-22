import numpy as np

Resistor_count = int(input("Number of Resistors: "))
Mesh_count = int(input("Number of Meshes (loops): "))
Voltage = float(input("Voltage Source: "))

Resistors = []
for r in range(Resistor_count):
    value = float(input(f"R{r+1} (Ohms): "))
    Resistors.append(value)

Mesh_resistors = []
print("\nresistors in each mesh like 1,2:")
for m in range(Mesh_count):
    input_str = input(f"Resistors in Mesh {m+1}: ")
    indices = list(map(int, input_str.strip().split(",")))
    Mesh_resistors.append(indices)


Voltages = []
for i in range(Mesh_count):
    Voltages.append(Voltage)

R = np.zeros((Mesh_count, Mesh_count))

for i in range(Mesh_count):
    for j in range(Mesh_count):
        if i == j:
            R[i][j] = sum([Resistors[r-1] for r in Mesh_resistors[i]])
            print(R)
        else:
            shared = set(Mesh_resistors[i]).intersection(Mesh_resistors[j])
            R[i][j] = -sum([Resistors[r-1] for r in shared])

# Solve R * I = V(B)
V = np.array(Voltages)

I = np.linalg.solve(R, V)
print("\nMesh Currents:")
for idx, current in enumerate(I):
    print(f"I{idx+1} = {current:.4f} A")

