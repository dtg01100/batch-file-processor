
import pytest
import convert_to_jolley_custom

@pytest.mark.timeout(5)
def test_convert_to_jolley_custom_invalid(tmp_path):
    input_file = tmp_path / "bad.edi"
    input_file.write_text("bad data")
    with pytest.raises(Exception):
        convert_to_jolley_custom.convert(str(input_file), str(tmp_path / "out.csv"))
