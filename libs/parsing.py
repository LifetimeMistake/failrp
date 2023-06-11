from datetime import timedelta
import re
# Regular expressions to extract values from the output string
elapsed_re = re.compile(r"Elapsed: ([\d:]+)")
remaining_re = re.compile(r"Remaining: ([\d:]+)")
completed_re = re.compile(r"Completed: +([\d.]+)%")
rate_re = re.compile(r"([\d.]+)GB/min")
current_block_re = re.compile(r"current block: +([\d,]+)")
total_block_re = re.compile(r"total block: +([\d,]+)")
complete_block_re = re.compile(r"Complete: +([\d.]+)%")
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def format_ocs(x):
    return ansi_escape.sub("", x).strip().replace(r"\s\s+", " ").replace('\r', '').replace('\n', "n")

def parse_output_string(output_str):

    # Check if the output string matches the expected format
    if not all(re.search(regex, output_str) for regex in [completed_re]):
        return False

    # Extract values from the output string using regular expressions
    try:
        elapsed = elapsed_re.search(output_str).group(1)
        remaining = remaining_re.search(output_str).group(1)
        completed = float(completed_re.search(output_str).group(1))
        rate = float(rate_re.search(output_str).group(1))
        current_block = int(current_block_re.search(output_str).group(1).replace(",", ""))
        total_block = int(total_block_re.search(output_str).group(1).replace(",", ""))
        complete_block = float(complete_block_re.search(output_str).group(1))

        # Convert elapsed and remaining time strings to timedelta objects for easier manipulation
        elapsed_td = timedelta(hours=int(elapsed[:2]), minutes=int(elapsed[3:5]), seconds=int(elapsed[6:]))
        remaining_td = timedelta(hours=int(remaining[:2]), minutes=int(remaining[3:5]), seconds=int(remaining[6:]))
    except: 
        return False
    # Return a list of extracted values
    return [elapsed_td, remaining_td, completed, rate, current_block, total_block, complete_block]