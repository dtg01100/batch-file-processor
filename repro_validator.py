import mtc_edi_validator
import tempfile
import os

valid_edi_content = """A000001INV001230115251000012345
B012345678901Product Description 1234561234567890100001000100050000         
C00100000123
A000002INV002340115251000054321
B012345678901Another Product   2345679876543210200002000200075000           
C00200000543
"""

with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
    f.write(valid_edi_content)
    temp_file = f.name

# Debug print lines lengths
with open(temp_file, "r") as f:
    for i, line in enumerate(f, 1):
        print(
            f"Line {i} length: {len(line)} (stripped: {len(line.strip())}) - Content: {repr(line)}"
        )

print(f"Testing file: {temp_file}")
try:
    result, line_number = mtc_edi_validator.check(temp_file)
    print(f"Result: {result}, Line: {line_number}")
except Exception as e:
    print(f"Exception: {e}")

os.unlink(temp_file)
