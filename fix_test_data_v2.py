import re
import sys

file_path = "tests/unit/test_edi_tweaks.py"

with open(file_path, "r") as f:
    lines = f.readlines()

new_lines = []

def process_b_record(line_content):
    # B + UPC + Desc + VendorItem(6) + Rest
    stripped = line_content.strip()
    if not stripped.startswith('B'):
        return line_content
        
    # Remove potential trailing newline char from the string literal representation
    has_newline_char = False
    if stripped.endswith('\\n'):
        stripped = stripped[:-2]
        has_newline_char = True
    elif stripped.endswith('\n'):
        stripped = stripped[:-1]
        
    # Find the vendor item (block of 6 digits followed by 6 digits for unit cost)
    # Search from right side or regex.
    # Matches `123456123456` pattern.
    match = re.search(r'(\d{6})(\d{6}\d+.*)$', stripped)
    if not match:
        # Maybe short record?
        # Check B012345678901Short Record     12345612345
        match = re.search(r'(\d{6})(\d+)$', stripped)
        
    if match:
        vendor_item = match.group(1)
        rest = match.group(2)
        # prefix is everything before vendor_item
        prefix = stripped[:match.start(1)]
        
        clean_prefix = prefix[1:] # Remove B
        
        # Assume first 12 chars are UPC candidate (from the broken test data)
        original_upc = clean_prefix[:12]
        original_desc = clean_prefix[12:]
        
        # Truncate UPC to 11
        # If it was spaces, it becomes 11 spaces.
        # If it was digits, it becomes 11 digits.
        new_upc = original_upc[:11]
        
        # Pad description to 25
        desc_text = original_desc.strip()
        new_desc = f"{desc_text:<25}"
        
        result = f"B{new_upc}{new_desc}{vendor_item}{rest}"
        if has_newline_char:
            result += '\\n'
        return result
        
    return line_content

for line in lines:
    # Detect strings that look like EDI records inside the python code
    # Usually in format: edi_content = "..."
    if 'edi_content = "' in line or 'return "' in line:
        parts = line.split('"')
        if len(parts) >= 3:
            content = parts[1]
            if content.startswith('B'):
                new_content = process_b_record(content)
                line = line.replace(content, new_content)
    
    # Handle multiline strings (lines starting with | B...)
    # The previous read output showed lines starting with | in the cat -n output, 
    # but actual file lines are just the content if inside multiline string?
    # No, python multiline strings usually indented.
    stripped = line.strip()
    if stripped.startswith('B') or (stripped.startswith('"B') and not stripped.endswith('"')):
         # It looks like a B record line in a multiline block
         clean_content = stripped.strip('"')
         # Remove trailing \n if present in string
         if clean_content.endswith('\\n'):
             clean_content = clean_content[:-2]
         
         if clean_content.startswith('B'):
             new_content = process_b_record(clean_content)
             
             # Reconstruct line
             # Find where the string starts
             start_idx = line.find('B')
             if start_idx != -1:
                 # Check if it was quoted
                 if start_idx > 0 and line[start_idx-1] == '"':
                      # It was "B..."
                      pass
                 
                 # We just replace the B-record part
                 # But we need to be careful not to mess up indentation or quotes
                 
                 # Easiest way: just replace the content substring
                 # But process_b_record returns stripped content
                 # We need to preserve original container
                 
                 # Let's try simple replace if unique
                 if clean_content in line:
                     # This might fail if process_b_record didn't change anything
                     pass
                     
                 # Actually, let's just rely on the structure we observed.
                 # "B0123... \n"
                 if stripped.startswith('"B'):
                     # Likely `edi_content = "B..."` handled above or multiline continuation
                     pass
                 else:
                     # Raw string in multiline?
                     pass

    new_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(new_lines)
