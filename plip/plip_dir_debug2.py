import os
import subprocess
import xml.etree.ElementTree as ET
import csv

# Change this to the path containing your PDB files
pdb_folder = "/Users/stepanchumakov/Nextcloud/Laboratory/AlphaFold/plip/plip/test1"

# Get a list of all PDB files in the folder
pdb_files = [f for f in os.listdir(pdb_folder) if f.lower().endswith('.pdb')]

# Define the mapping for interaction types:
interaction_types = {
    'hydrophobic_interactions': ('hydrophobic_interaction', 'Hydrophobic Interactions'),
    'hydrogen_bonds': ('hydrogen_bond', 'Hydrogen Bonds'),
    'salt_bridges': ('salt_bridge', 'Salt Bridges'),
    'pi_cation_interactions': ('pi_cation_interaction', 'pi-Cation Interactions'),
    'water_bridges': ('water_bridge', 'Water Bridges'),
    'pi_stacks': ('pi_stack', 'Pi Stacks'),
    'halogen_bonds': ('halogen_bond', 'Halogen Bonds'),
    'metal_complexes': ('metal_complex', 'Metal Complexes'),
}

# Dictionary to hold counts for each file.
file_counts = {}

# Loop over each PDB file
for pdb_file in pdb_files:
    pdb_path = os.path.join(pdb_folder, pdb_file)
    print(f"Processing {pdb_file}...")
    
    # Run PLIP for the given PDB file with chains H and T,
    # outputting XML to stdout.
    cmd = ["plipcmd.py", "-x", "-O", "-q", "-f", pdb_path, "--chains", "[['H'], ['T']]"]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running PLIP on {pdb_file}: {e}")
        continue

    # Combine stdout and stderr
    raw_output = result.stdout.decode("utf-8", errors="ignore") + result.stderr.decode("utf-8", errors="ignore")
    
    # Extract the valid XML portion by finding <report> and </report>
    xml_start = raw_output.find("<report>")
    if xml_start == -1:
        print(f"No <report> tag found in output for {pdb_file}. Here is a preview:\n{raw_output[:300]}\nSkipping this file.")
        continue
    xml_end = raw_output.rfind("</report>")
    if xml_end == -1:
        print(f"No closing </report> tag found for {pdb_file}. Skipping this file.")
        continue
    xml_str = raw_output[xml_start: xml_end + len("</report>")]
    
    # Parse the XML output
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"Error parsing XML for {pdb_file}: {e}")
        continue
    
    # Locate the <interactions> element (nested under <bindingsite>)
    interactions = root.find('.//interactions')
    if interactions is None:
        print(f"No <interactions> element found for {pdb_file}.")
        continue

    # Count interactions for each type in this file
    counts = {}
    for container_tag, (child_tag, display_name) in interaction_types.items():
        container = interactions.find(container_tag)
        if container is not None:
            if child_tag:
                count = len(container.findall(child_tag))
            else:
                count = len(list(container))
        else:
            count = 0
        counts[display_name] = count

    file_counts[pdb_file] = counts

# Write the combined counts to a CSV.
output_csv = "combined_interaction_counts.csv"
interaction_names = [display for _, display in interaction_types.values()]
sorted_files = sorted(file_counts.keys())

with open(output_csv, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    header = ["Interaction Type"] + sorted_files
    writer.writerow(header)
    
    for interaction in interaction_names:
        row = [interaction]
        for pdb_file in sorted_files:
            count = file_counts[pdb_file].get(interaction, 0)
            row.append(count)
        writer.writerow(row)

print(f"Combined interaction counts have been written to {output_csv}")