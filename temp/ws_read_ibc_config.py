import zipfile, re

jar = r"C:\IBC\IBC.jar"
with zipfile.ZipFile(jar, 'r') as z:
    names = z.namelist()
    # find config-related files
    config_files = [n for n in names if 'config' in n.lower() or 'ini' in n.lower() or 'sample' in n.lower() or 'readme' in n.lower() or 'sso' in n.lower()]
    print("Config-related files in IBC.jar:")
    for f in config_files:
        print(" ", f)

    # also search for SSO, UseSSO, s3store, login dialog references in any text file
    print("\nSearching for SSO/login/dialog references in IBC.jar classes:")
    keywords = [b'UseSSO', b'SsoEnabled', b'loginDialog', b'1112', b'StoreSettingsOnServer', b'login dialog']
    for name in names:
        if name.endswith('.class') or name.endswith('.properties') or name.endswith('.txt') or name.endswith('.ini'):
            try:
                data = z.read(name)
                for kw in keywords:
                    if kw.lower() in data.lower():
                        print(f"  [{name}] contains: {kw.decode()}")
                        break
            except:
                pass
