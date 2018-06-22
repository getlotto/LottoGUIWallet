# -*- mode: python -*-

block_cipher = None


a = Analysis(['wallet.py'],
             pathex=['D:\\Onedrive\\GitHUB\\LottoGUIWallet'],
             binaries=[],
             datas=[('Resources', 'Resources')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='LottoGUI',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='Resources\\icons\\lotto_icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='LottoGUI')
