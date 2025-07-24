# Function to check if a line contains a received UPDATE event
def is_received_event(line):
    return 'rcvd UPDATE' in line and 'DENIED' not in line and 'duplicate ignored' not in line

# Main function to read bgpd.log and write received events to received_events.txt
def parse_received_events():
    with open('bgpd.log', 'r') as input_file:
        with open('received_events.txt', 'w') as output_file:
            for line in input_file:
                if is_received_event(line):
                    output_file.write(line)

    print("Parsed BGP received events saved to received_events.txt")

# Run the parser
if __name__ == "__main__":
    parse_received_events()