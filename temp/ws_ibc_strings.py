import zipfile, re

jar = r"C:\IBC\IBC.jar"
targets = [
    'ibcalpha/ibc/LoginFrameHandler$1.class',
    'ibcalpha/ibc/AbstractLoginHandler.class',
    'ibcalpha/ibc/IbcTws.class',
    'ibcalpha/ibc/SessionManager.class',
    'ibcalpha/ibc/Settings.class',
]

with zipfile.ZipFile(jar, 'r') as z:
    all_names = z.namelist()
    settings_files = [n for n in all_names if 'Setting' in n and n.endswith('.class')]
    print("Settings classes:", settings_files)

    for name in targets + settings_files:
        if name not in all_names:
            continue
        data = z.read(name)
        # extract readable ASCII strings >= 6 chars
        strings = re.findall(rb'[\x20-\x7e]{6,}', data)
        relevant = [s.decode() for s in strings if any(k in s.lower() for k in
            [b'sso', b'store', b'login', b'dialog', b'credential', b'bypass',
             b'autolog', b'token', b'session', b'useremot', b'password',
             b'ibloginid', b'tradingmode', b'relogin', b'2fa', b'twofa'])]
        if relevant:
            print(f"\n=== {name} ===")
            for s in sorted(set(relevant)):
                print(f"  {s}")
