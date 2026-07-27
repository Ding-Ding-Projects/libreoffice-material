import pathlib
import xml.etree.ElementTree as ET

# Check which dialogs exist
ui_dir = pathlib.Path('cui/uiconfig/ui/')
dialogs = ['extensionmanager.ui', 'dictionarylist.ui', 'spelloptionsdialog.ui', 'additionsfragment.ui']
for d in dialogs:
    p = ui_dir / d
    print(f'{d}: {"EXISTS" if p.exists() else "MISSING"}')
