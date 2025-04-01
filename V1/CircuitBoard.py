import numpy as np

def get_input(prompt, data_type):
    """Gets user input and converts it to the specified data type."""
    while True:
        try:
            value = input(prompt)
            return data_type(value)
        except ValueError:
            print(f"Invalid input. Please enter a {data_type.__name__}.")

def get_resistor_values(num_resistors):
    """Gets resistance values for all resistors."""
    resistor_values = {}
    for i in range(num_resistors):
        while True:
            r_val = get_input(f"Enter resistance for R{i + 1} (Ohms): ", float)
            if r_val > 0:
                resistor_values[i + 1] = r_val
                break
            else:
                print("Resistance must be greater than 0.")
    return resistor_values

def get_mesh_definitions(num_meshes, resistor_values):
    """Gets the resistor IDs for each mesh."""
    mesh_definitions = {}
    for i in range(num_meshes):
        while True:
            res_ids_str = input(f"Enter resistor IDs for Mesh {i + 1} (comma-separated): ")
            res_ids = [int(r_id.strip()) for r_id in res_ids_str.split(',')]
            if all(r_id in resistor_values for r_id in res_ids):
                mesh_definitions[i + 1] = res_ids
                break
            else:
                print("Invalid resistor IDs.  Please check and try again.")
    return mesh_definitions

def get_shared_resistors(num_resistors, num_meshes):
    """Gets the shared resistor information."""
    shared_resistors = []
    num_shared = get_input("Enter the number of shared resistors: ", int)
    for _ in range(num_shared):
        while True:
            shared_input = input("Enter shared resistor (R_ID, Mesh_ID1, Mesh_ID2): ")
            parts = shared_input.split(',')
            if len(parts) != 3:
                print("Invalid format.  Use 'R_ID, Mesh_ID1, Mesh_ID2'")
                continue
            try:
                r_id, mesh1_id, mesh2_id = map(int, map(str.strip, parts))
                if 1 <= r_id <= num_resistors and 1 <= mesh1_id <= num_meshes and 1 <= mesh2_id <= num_meshes and mesh1_id != mesh2_id:
                    shared_resistors.append((r_id, mesh1_id, mesh2_id))
                    break
                else:
                    print("Invalid input.")
            except ValueError:
                print("Invalid input. Please enter integers.")
    return shared_resistors

def calculate_mesh_currents(num_meshes, resistor_values, mesh_definitions, shared_resistors, voltage_source):
    """Calculates the mesh currents."""
    R_matrix = np.zeros((num_meshes, num_meshes))
    V_vector = np.zeros(num_meshes)

    for i in range(num_meshes):
        mesh_id = i + 1
        res_ids = mesh_definitions[mesh_id]
        R_matrix[i, i] = sum(resistor_values[r_id] for r_id in res_ids)
        V_vector[i] = voltage_source

    for r_id, mesh1_id, mesh2_id in shared_resistors:
        r_val = resistor_values[r_id]
        idx1, idx2 = mesh1_id - 1, mesh2_id - 1
        R_matrix[idx1, idx2] -= r_val
        R_matrix[idx2, idx1] -= r_val

    try:
        mesh_currents = np.linalg.solve(R_matrix, V_vector)
        return mesh_currents, R_matrix, V_vector  # Return R_matrix and V_vector
    except np.linalg.LinAlgError:
        print("Error: Cannot solve the system.")
        return None, None, None

def display_results(R_matrix, V_vector, mesh_currents):
    """Displays the results."""
    print("\n--- Input Summary ---")
    print(f"Resistance Matrix [R]:\n{R_matrix}")
    print(f"Voltage Vector [V]:\n{V_vector}")

    if mesh_currents is not None:
        print("\n--- Results ---")
        print("Mesh Currents [I] (Amperes):")
        for i, current in enumerate(mesh_currents):
            print(f"  Mesh {i + 1}: {current:.4f}")
    else:
        print("\nCalculation failed.")

def main():
    """Main function to run the calculator."""
    print("Welcome to the Mesh Analysis Calculator (Text Version)")

    num_resistors = get_input("Enter the number of resistors: ", int)
    voltage_source = get_input("Enter the main voltage source (V): ", float)
    num_meshes = get_input("Enter the number of meshes: ", int)

    resistor_values = get_resistor_values(num_resistors)
    mesh_definitions = get_mesh_definitions(num_meshes, resistor_values)
    shared_resistors = get_shared_resistors(num_resistors, num_meshes)

    print("\n--- Calculating Mesh Currents ---")
    mesh_currents, R_matrix, V_vector = calculate_mesh_currents(num_meshes, resistor_values, mesh_definitions, shared_resistors, voltage_source)

    if mesh_currents is not None:
        display_results(np.array(R_matrix), np.array(V_vector), mesh_currents)
    else:
        print("Calculation Failed")

if __name__ == "__main__":
    main()
