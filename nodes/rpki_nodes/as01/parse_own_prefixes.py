# Function to parse AS path and determine if the AS declares its own prefix
def parse_as_path(line):
    if 'path' in line:
        path_part = line.split('path ')[1]
        as_path = [int(x) for x in path_part.split() if x.isdigit()]
        if as_path:
            origin_as = as_path[-1]  # Last AS is the origin
            # Check if origin AS appears only at the end
            if as_path.count(origin_as) == 1:
                return origin_as, line  # Return both AS and full line
    return None, None

# Main function to read received_events.txt and write ASes with their announcements to own_prefix.txt
def parse_own_prefixes():
    declaring_ases = {}  # Dictionary to store AS and its announcements
    
    with open('received_events.txt', 'r') as input_file:
        for line in input_file:
            declaring_as, full_line = parse_as_path(line)
            if declaring_as is not None:
                if declaring_as not in declaring_ases:
                    declaring_ases[declaring_as] = []
                declaring_ases[declaring_as].append(full_line)

    # Write results to own_prefix.txt
    with open('own_prefix.txt', 'w') as output_file:
        if declaring_ases:
            output_file.write("ASes declaring their own prefixes with announcements:\n")
            for as_num in sorted(declaring_ases.keys()):
                output_file.write(f"\nAS {as_num}:\n")
                for announcement in declaring_ases[as_num]:
                    output_file.write(f"{announcement}")
        else:
            output_file.write("No ASes found declaring their own prefixes.\n")

    print("Parsed ASes with their announcements saved to own_prefix.txt")

# Run the parser
if __name__ == "__main__":
    parse_own_prefixes()