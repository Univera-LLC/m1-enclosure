"""Independent toolpath preflight. No printer I/O; G-code stays in the scratch directory."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
TMP=HERE.parents[2]/"tmp/d2-slicer"
DEFAULT=TMP/"PrusaSlicer-2.9.7/prusa-slicer-console.exe"
PRESETS={"printer":"Creality Ender-3 Pro (0.4 mm nozzle)","print":"0.20 mm NORMAL (0.4 mm nozzle) @CREALITY","filament":"Generic PETG @CREALITY"}

def config(exe):
    vendor=exe.parent/"resources/profiles/Creality.ini"
    ini=configparser.RawConfigParser(strict=False); ini.read(vendor,encoding="utf-8-sig")
    def expand(kind,name):
        own=dict(ini[f"{kind}:{name}"]); values={}
        for parent in own.pop("inherits","").split(";"):
            if parent.strip(): values.update(expand(kind,parent.strip()))
        return {**values,**own}
    values={}
    for kind,name in PRESETS.items(): values.update(expand(kind,name))
    # Profile selector metadata isn't part of a flat config. Only the geometry
    # and toolpaths matter here; omit printer start/stop/serial instructions.
    for key in ("compatible_printers_condition","compatible_prints_condition","renamed_from","alias"):
        values.pop(key,None)
    values.update(start_gcode="",end_gcode="",support_material="0",binary_gcode="0",gcode_comments="1",skirts="0")
    TMP.mkdir(exist_ok=True)
    cfg=TMP/"d2-inspect.ini"
    cfg.write_text("\n".join(k+" = "+v for k,v in sorted(values.items()))+"\n",encoding="utf-8")
    return cfg,hashlib.sha256(vendor.read_bytes()).hexdigest()

def slice_one(exe,cfg,stl,seam=None,panel_generator=None):
    dest=TMP/(stl.stem+("-"+(seam or panel_generator) if seam or panel_generator else "")+".gcode")
    args=[str(exe),"--datadir",str(TMP/"presets"),"--load",str(cfg),"--threads","3"]
    if seam:args.extend(["--seam-position",seam])
    if stl.name=="02-flat-rear-panel.stl":
        args.extend(["--fill-density","100%","--fill-pattern","rectilinear","--perimeter-generator",panel_generator or "classic"])
    args.extend(["--export-gcode","--output",str(dest),str(stl)])
    run=subprocess.run(args,capture_output=True,text=True,encoding="utf-8",errors="replace")
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    g=dest.read_text(encoding="utf-8")
    layers=[float(v) for v in re.findall(r"^;Z:([\d.]+)",g,re.M)]
    assert layers and len(layers)==len(set(layers)) and layers==sorted(layers),stl
    types=sorted(set(re.findall(r"^;TYPE:(.+)$",g,re.M)))
    assert "External perimeter" in types and not any("Support" in t for t in types),(stl,types)
    lines=(run.stdout+run.stderr).splitlines();warnings=[];capture=False
    for line in lines:
        if re.search(r"\b(error|warning)\b",line,re.I):capture=True
        elif re.match(r"\d+ =>",line):capture=False
        if capture and line.strip():warnings.append(line.strip())
    settings=dict(re.findall(r"^; (seam_position|fill_density|fill_pattern|support_material|perimeter_generator) = (.+)$",g,re.M))
    assert settings["support_material"]=="0" and (seam is None or settings["seam_position"]==seam),settings
    if stl.name=="02-flat-rear-panel.stl":
        assert settings["fill_density"]=="100%" and settings["fill_pattern"]=="rectilinear" and settings["perimeter_generator"]==(panel_generator or "classic"),settings
    return {"layers":len(layers),"first_last_z_mm":[layers[0],layers[-1]],"types":types,"seam_position":settings["seam_position"],"perimeter_generator":settings["perimeter_generator"],
            "bridge_regions":g.count(";TYPE:Bridge infill"),"warnings":warnings,
            "toolpath_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"input_sha256":hashlib.sha256(stl.read_bytes()).hexdigest()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--slicer",type=Path,default=DEFAULT);parser.add_argument("--probe",type=Path);args=parser.parse_args()
    exe=args.slicer.resolve();cfg,vendor=config(exe)
    if args.probe:print(slice_one(exe,cfg,args.probe.resolve()));return
    parts={p.name:slice_one(exe,cfg,p) for p in sorted((HERE/"print").glob("*.stl"))}
    expected=json.loads((HERE/"print/stl-checks.json").read_text())["parts"]
    assert parts.keys()==expected.keys() and all(p["input_sha256"]==expected[n]["sha256"] for n,p in parts.items())
    assert parts["02-flat-rear-panel.stl"]["bridge_regions"]==0 and not any(x["warnings"] for x in parts.values()), parts
    from panel_toolpaths import matched_mouths
    panel_bbox=json.loads((HERE/"cad-validation.json").read_text())["bodies"]["D2_SLIDING_IO_PLATE"]["bbox"]
    openings=matched_mouths((TMP/"02-flat-rear-panel.gcode").read_text(encoding="utf-8"),panel_bbox)
    assert len(openings)==parts["02-flat-rear-panel.stl"]["layers"]==9 and set(openings.values())=={8},openings
    # Preserve the slicer's diagnostic on this exact export. This alternative
    # is not the profile in the kit; its exit code alone is not acceptance.
    alternate=slice_one(exe,cfg,HERE/"print/02-flat-rear-panel.stl",panel_generator="arachne")
    assert alternate["input_sha256"]==parts["02-flat-rear-panel.stl"]["input_sha256"]
    # The tall ends of the track once caused a fragile-part warning dependent
    # on seam placement. Exercise all three placements on the shipping STL.
    base=HERE/"print/03-monolithic-base.stl";default=parts[base.name]
    seams={default["seam_position"]:default}
    for seam in ("aligned","rear"):seams[seam]=slice_one(exe,cfg,base,seam)
    assert len(seams)==3 and all(p["input_sha256"]==default["input_sha256"] and not p["warnings"] for p in seams.values()),seams
    report={"scope":"Offline slicing scenario; no hardware used, actual machine/nozzle/filament not measured. No physical fit, durability, heat or RF signoff. G-code not included in kits.",
        "slicer":subprocess.check_output([str(exe),"--help"],encoding="utf-8",errors="replace").splitlines()[0],
        "presets":PRESETS,"overrides":"supports, skirt, binary G-code, start/end script disabled; panel only: Classic perimeters, 100% rectilinear; model at 100% in supplied bed orientation","vendor_ini_sha256":vendor,
        "parts":parts,"full_base_seam_checks":seams,"distinct_port_perimeters_at_layer_z_mm":openings,"panel_alternative_not_recommended":alternate}
    (HERE/"print/slice-checks.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print({k:(v["layers"],v["bridge_regions"]) for k,v in parts.items()})
if __name__=="__main__":main()
