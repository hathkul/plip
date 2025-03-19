import os
import subprocess
import xml.etree.ElementTree as ET
import csv
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Run PLIP on all PDB files in a folder and generate a CSV of interaction counts."
    )
    parser.add_argument("folder", help="Path to the folder containing PDB files.")
    parser.add_argument(
        "--output", default="combined_interaction_counts.csv",
        help="Output CSV filename (default: combined_interaction_counts.csv)"
    )
    args = parser.parse_args()

    pdb_folder = args.folder

    # List all PDB files in the folder
    pdb_files = [f for f in os.listdir(pdb_folder) if f.lower().endswith('.pdb')]
    if not pdb_files:
        print("No PDB files found in the specified folder.")
        return

    # Define the mapping for interaction types:
    # key: container tag in the XML
    # value: tuple(child tag to count, display name)
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
    # Key = filename; Value = dictionary {interaction_display_name: count}
    file_counts = {}

    # Loop over each PDB file
    for pdb_file in pdb_files:
        pdb_path = os.path.join(pdb_folder, pdb_file)
        print(f"Processing {pdb_file}...")
        
        # Run PLIP with chain restrictions (chains H and T), XML output, and quiet mode.
        # Note: The --chains argument is passed as a string.
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
        
        # Extract valid XML by finding <report> and </report>
        xml_start = raw_output.find("<report>")
        if xml_start == -1:
            print(f"No <report> tag found in output for {pdb_file}. Here is a preview:\n{raw_output[:300]}\nSkipping this file.")
            continue
        xml_end = raw_output.rfind("</report>")
        if xml_end == -1:
            print(f"No closing </report> tag found for {pdb_file}. Skipping this file.")
            continue
        xml_str = raw_output[xml_start: xml_end + len("</report>")]

        # Parse the XML
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            print(f"Error parsing XML for {pdb_file}: {e}")
            continue
        
        # Find the <interactions> element (nested under <bindingsite>)
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

    if not file_counts:
        print("No valid PLIP output processed.")
        return

    # Sort filenames (columns) by total interactions (largest to smallest)
    sorted_files = sorted(
        file_counts.keys(),
        key=lambda f: sum(file_counts[f].values()),
        reverse=True
    )

    # Get a list of interaction display names (rows) in a consistent order
    interaction_names = [display for _, display in interaction_types.values()]

    # Write the combined counts to a CSV file
    with open(args.output, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        header = ["Interaction Type"] + sorted_files
        writer.writerow(header)
        
        for interaction in interaction_names:
            row = [interaction]
            for pdb_file in sorted_files:
                count = file_counts[pdb_file].get(interaction, 0)
                row.append(count)
            writer.writerow(row)

    print(f"Combined interaction counts have been written to {args.output}")

if __name__ == '__main__':
    main()
