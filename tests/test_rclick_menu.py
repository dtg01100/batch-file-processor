import pytest
import rclick_menu

@pytest.mark.timeout(5)
def test_rclick_menu_invalid_widget():
    with pytest.raises(Exception):
        rclick_menu.RightClickMenu(None)
