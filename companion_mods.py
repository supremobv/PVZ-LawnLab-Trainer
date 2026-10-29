"""Credited upstream catalog and an opt-in, separately installed companion."""
import hashlib,json,subprocess,urllib.request,zipfile,io
from pathlib import Path,PurePosixPath
from resource_mods import library
from studio_storage import atomic_bytes

CATALOG=[dict(id='pvza11y',name='PvZA11y',author='CG8516 and contributors',license='MIT',source='https://github.com/CG8516/PvZA11y',editions=['goty'],kind='companion',description='Keyboard/controller and accessibility support. Upstream supports DVD GOTY 1.2.0.1073 and Steam GOTY, not Classic. Run separately with LawnLab disconnected; restart PVZ before returning to trainer controls.'),
 dict(id='archipelago',name='Archipelago Randomizer',author='Victor Tran / vicr123; Bonzorio and contributors',license='MIT',source='https://github.com/vicr123/PvZ-Stable-Decompile-AP',editions=[],kind='standalone',description='Separate recompiled game and multiworld randomizer. Not a resource pack for either stock executable; use its upstream installation, not Apply to this game.'),
 dict(id='portable',name='PvZ-Portable LuaJIT mods',author='hello-lisai and PvZ-Portable contributors',license='LGPL-3.0-or-later',source='https://github.com/hello-lisai/PvZ-Portable-LuaJIT',editions=[],kind='standalone',description='Community engine with Lua mod APIs. Requires its own executable and user-supplied assets. Its Lua mods cannot be applied to stock GOTY/Classic.')]

def install_a11y():
 url='https://api.github.com/repos/CG8516/PvZA11y/releases'
 request=urllib.request.Request(url,headers={'User-Agent':'LawnLab-mod-catalog'})
 with urllib.request.urlopen(request,timeout=30)as response:releases=json.load(response)
 release=next((r for r in releases if r.get('tag_name')=='beta.1.17.2'),None)
 if release is None:raise RuntimeError('The reviewed PvZA11y release is no longer available from upstream.')
 asset=next(a for a in release['assets']if a['name']=='PvZA11y_Beta1.17.2.zip')
 url=asset['browser_download_url']
 if not url.startswith('https://github.com/CG8516/PvZA11y/releases/download/beta.1.17.2/'):raise RuntimeError('Unexpected upstream download URL.')
 if asset['size']>20_000_000:raise RuntimeError('Unexpected companion download size.')
 with urllib.request.urlopen(url,timeout=45)as response:data=response.read(20_000_001)
 if len(data)!=asset['size']:raise RuntimeError('The companion download was truncated.')
 if hashlib.sha256(data).hexdigest()!='61fab1b3df3fad138c0409a426321e7dc6fc513ed4f02a0a536ffdbab13f42ea':raise RuntimeError('The reviewed upstream archive hash changed; no companion was installed.')
 folder=library()/'companions/pvza11y-beta.1.17.2'
 with zipfile.ZipFile(io.BytesIO(data))as archive:
  if len(archive.infolist())>1000 or sum(x.file_size for x in archive.infolist())>100_000_000:raise RuntimeError('Unexpected companion archive size.')
  for item in archive.infolist():
   p=PurePosixPath(item.filename.replace('\\','/'))
   if p.is_absolute()or'..'in p.parts or':'in item.filename or(item.external_attr>>16)&0xF000==0xA000:raise RuntimeError('Companion archive contains an unsafe path.')
   if not item.is_dir():atomic_bytes(folder/str(p),archive.read(item))
  executables=list(folder.rglob('PvZA11y.exe'))
  if len(executables)!=1:raise RuntimeError('The companion executable is ambiguous.')
 with urllib.request.urlopen('https://raw.githubusercontent.com/CG8516/PvZA11y/master/LICENSE.txt',timeout=30)as response:license_text=response.read(100_000)
 atomic_bytes(folder/'UPSTREAM-LICENSE.txt',license_text)
 metadata=dict(CATALOG[0],release=release['tag_name'],zip_sha256=hashlib.sha256(data).hexdigest(),url=url,executable=str(executables[0]),exe_sha256=hashlib.sha256(executables[0].read_bytes()).hexdigest())
 atomic_bytes(folder/'lawnlab-install.json',json.dumps(metadata,indent=2).encode());return metadata
def installed_a11y():
 p=library()/'companions/pvza11y-beta.1.17.2/lawnlab-install.json'
 return json.loads(p.read_text())if p.exists()else None
def launch_a11y():
 metadata=installed_a11y()
 if not metadata:raise RuntimeError('Install the reviewed upstream companion first.')
 from trainer_backend import candidates,GotyTrainer
 pid,kind=candidates()
 if kind is not GotyTrainer:raise RuntimeError('PvZA11y does not support the installed Classic edition.')
 p=Path(metadata['executable'])
 if not p.is_file()or not p.resolve().is_relative_to((library()/'companions').resolve()):raise RuntimeError('Companion installation is missing or moved.')
 if hashlib.sha256(p.read_bytes()).hexdigest()!=metadata.get('exe_sha256'):raise RuntimeError('The companion executable changed. Reinstall the reviewed release.')
 subprocess.Popen([str(p)],cwd=str(p.parent));return'PvZA11y launched separately. Restart PVZ before reconnecting LawnLab.'
