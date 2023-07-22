import re
import csv


def to_csv(input_file, output_file):
# Define the regular expressions to extract the required information
    client_id_pattern = r'print_dict.*client_id\s*:\s*(.*)'
    timestamp_pattern = r'print_dict.*timestamp\s*:\s*([\d-]+\s[\d:]+)'
    performance_pattern = r'print_dict.*performance\s*:\s*([0-9.]+)'
    loss_pattern = r'print_dict.*loss\s*:\s*([0-9.]+)'
    message_type_pattern = r'message_type\s*:\s*(client_notify|client\.notify\.evaluation)'

    with open(input_file, 'r') as file:
        log_lines = file.readlines()

# Initialize lists to store the extracted values
    timestamps = []
    client_ids = []
    performances = []
    losses = []

    is_message_matched = False
    old_len = 0
    prev_line = ''
    for line in log_lines:
        if re.search(message_type_pattern, line):
            is_message_matched = True
        if is_message_matched:
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match:
                timestamps.append(timestamp_match.group(1).strip())
            else:
                timestamp_match = re.search(timestamp_pattern, prev_line)
                if timestamp_match:
                    timestamps.append(timestamp_match.group(1).strip())
            client_id_match = re.search(client_id_pattern, line)
            if client_id_match:
                client_ids.append(client_id_match.group(1).strip())
            performance_match = re.search(performance_pattern, line)
            if performance_match:
                performances.append(performance_match.group(1))
            loss_match = re.search(loss_pattern, line)
            if loss_match:
                losses.append(loss_match.group(1))

        if len(timestamps) != old_len and len(timestamps) == len(client_ids) == len(performances) == len(losses):
            old_len += 1
            is_message_matched = False
        prev_line = line

# Write the extracted values to the CSV file
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'client_id', 'performance', 'loss'])
        for i in range(len(client_ids)):
            writer.writerow([timestamps[i].strip(), client_ids[i].strip(), performances[i], losses[i]])

    print(f"Values written to {output_file} successfully with {len(timestamps)} records.")
# client_ids = set(client_ids)
    for client_id in set(client_ids):
        print(f"{client_id}: {client_ids.count(client_id)} records.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file', help='Input log file', default='server.log')
    parser.add_argument('-o', '--output_file', help='Output CSV file', default='output.csv')
    args = parser.parse_args()
    to_csv(args.input_file, args.output_file)


