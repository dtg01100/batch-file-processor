import re

file_path = "tests/unit/test_edi_tweaks.py"

with open(file_path, "r") as f:
    content = f.read()

# Fix A records: AxxxxxxINVxxxxx01MMDDYY... -> AxxxxxxINVxxxxx  MMDDYY...
# Pattern: (A\d{6}INV\d{5})01(\d{6})
# This handles INV0012301152510 -> INV00123  011525
# Wait, let's look at specific strings.
# A000001INV00123011525
# A000002INV00234012225
# A000003INV00555011525

def fix_a_record(match):
    # match.group(0) is the whole A record start
    # We expect A...INV...01...
    # We want to insert 2 spaces after INV... and before 01... 
    # BUT wait, the '01' is currently part of Invoice Number (according to parser).
    # And the date misses '01'.
    # So we want to move '01' from Invoice Number to Date, and put 2 spaces in Invoice Number.
    
    # Example: A000001INV00123011525
    # Target:  A000001INV00123  011525
    
    # We can match strictly: (A\d{6}INV\d{5})01(\d{4})
    # Group 1: A000001INV00123
    # Group 2: 1525 (Year part? No, 1525 is DayYear?)
    # Original: INV0012301 (10 chars). Next: 152510 (6 chars).
    # If we change to INV00123   (10 chars). Next: 011525 (6 chars).
    # So we are effectively taking '01' from end of Invoice Num and prepending to Date.
    # And replacing the hole in Invoice Num with '  '.
    
    full_str = match.group(0)
    # A (1) + Vendor (6) + INV (3) + Num (5) = 15 chars.
    # Then '01' (2 chars)
    # Then DateRest (4 chars)
    
    prefix = full_str[:15] # A000001INV00123
    middle = full_str[15:17] # 01
    suffix = full_str[17:] # 1525
    
    return f"{prefix}  {middle}{suffix}"

content = re.sub(r"A\d{6}INV\d{5}01\d{4}", fix_a_record, content)

# Fix specific broken one: A000001INV00123ABCD25
# Original: A000001INV00123ABCD25
# It has 'ABCD' where '0115' was?
# No, A000001INV00123ABCD25
# Inv Num: INV00123AB (10 chars)
# Date: CD25..
# We want Inv Num: INV00123  
# Date: ABCD25
# So insert 2 spaces after INV00123.
content = content.replace("A000001INV00123ABCD25", "A000001INV00123  ABCD25")


# Fix B records
# 1. 12-digit UPC -> 11-digit UPC
# Pattern: B(\d{12}) -> B(\d{11})
# This removes the last digit (check digit)
content = re.sub(r"B(\d{11})\d", r"B\1", content)

# 2. 12 spaces -> 11 spaces
content = content.replace("B            ", "B           ")

# 3. 8 digits + 4 spaces -> 8 digits + 3 spaces
# Pattern: B(\d{8})    
content = re.sub(r"B(\d{8})    ", r"B\1   ", content)

with open(file_path, "w") as f:
    f.write(content)

