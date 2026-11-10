"""Package source only; credentials, upstream copies and build outputs are excluded."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from ui_assets import WEB_FILES


def main():
    source=Path(__file__).resolve().parent
    workspace=source.parents[1]
    project=Path(r'E:\Warcraft-III-Online').resolve()
    target=(project/'deploy/HostMap').resolve()
    if not target.is_relative_to(project): raise RuntimeError('Unexpected project target')
    target.mkdir(parents=True,exist_ok=True)
    files=sorted(source.glob('*.py'))+[source/n for n in ('Dockerfile','ready.hpp','test_ready.cpp','README.ru.md','README.guest.ru.md')]
    files += [source/'web'/n for n in WEB_FILES]
    manifest={}
    for path in files:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        relative=path.relative_to(source).as_posix()
        dest=target/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:
            shutil.copyfile(path,dest)
        manifest[relative]=digest
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output=workspace/'outputs/HostMap-2026-11-10.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files: archive.write(path,'HostMap/'+path.relative_to(source).as_posix())
        archive.write(target/'manifest.json','HostMap/manifest.json')
    print(json.dumps(dict(source_files=len(files),project=str(target),zip=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__=='__main__': main()
